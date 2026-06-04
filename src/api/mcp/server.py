"""MCP server implementing JSON-RPC 2.0 transport with tool, resource, and prompt support."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


ERROR_PARSE = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32603


class MCPServer:
    def __init__(self, name: str = "trust-safety-mcp", version: str = "1.0.0") -> None:
        self.name = name
        self.version = version
        self._tools: dict[str, dict[str, Any]] = {}
        self._resources: dict[str, dict[str, Any]] = {}
        self._prompts: dict[str, dict[str, Any]] = {}
        self._tool_handlers: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._resource_handlers: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._prompt_handlers: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._running = False
        self._read_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._write_queue: asyncio.Queue[str] = asyncio.Queue()

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[..., Awaitable[Any]],
    ) -> None:
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }
        self._tool_handlers[name] = handler

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "application/json",
        handler: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self._resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description,
            "mimeType": mime_type,
        }
        if handler is not None:
            self._resource_handlers[uri] = handler

    def register_prompt(
        self,
        name: str,
        description: str,
        arguments: list[dict[str, Any]] | None = None,
        handler: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self._prompts[name] = {
            "name": name,
            "description": description,
            "arguments": arguments or [],
        }
        if handler is not None:
            self._prompt_handlers[name] = handler

    def _make_response(
        self, request_id: str | int | None, result: Any, error: dict[str, Any] | None = None
    ) -> str:
        response: dict[str, Any] = {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
        }
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result
        return json.dumps(response)

    def _make_error(
        self, request_id: str | int | None, code: int, message: str, data: Any = None
    ) -> str:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return self._make_response(request_id, None, error=error)

    async def handle_request(self, raw: str) -> str:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return self._make_error(None, ERROR_PARSE, "Parse error")

        if not isinstance(msg, dict):
            return self._make_error(None, ERROR_INVALID_REQUEST, "Invalid request")

        method = msg.get("method")
        params = msg.get("params", {})
        request_id = msg.get("id")

        if method == "initialize":
            return self._make_response(request_id, {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {"name": self.name, "version": self.version},
            })

        if method == "ping":
            return self._make_response(request_id, {})

        if method == "notifications/initialized":
            return self._make_response(request_id, {})

        if method == "tools/list":
            return self._make_response(request_id, {"tools": list(self._tools.values())})

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name not in self._tool_handlers:
                return self._make_error(request_id, ERROR_METHOD_NOT_FOUND, f"Tool not found: {tool_name}")
            try:
                result = await self._tool_handlers[tool_name](**arguments)
                if isinstance(result, dict) and "content" in result:
                    return self._make_response(request_id, result)
                return self._make_response(request_id, {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                })
            except MCPError as e:
                return self._make_error(request_id, e.code, e.message, e.data)
            except Exception as e:
                return self._make_error(request_id, ERROR_INTERNAL, str(e))

        if method == "resources/list":
            return self._make_response(request_id, {"resources": list(self._resources.values())})

        if method == "resources/read":
            uri = params.get("uri")
            if uri not in self._resource_handlers:
                return self._make_error(request_id, ERROR_METHOD_NOT_FOUND, f"Resource not found: {uri}")
            try:
                content = await self._resource_handlers[uri](uri)
                return self._make_response(request_id, {
                    "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(content)}]
                })
            except Exception as e:
                return self._make_error(request_id, ERROR_INTERNAL, str(e))

        if method == "prompts/list":
            return self._make_response(request_id, {"prompts": list(self._prompts.values())})

        if method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments", {})
            if prompt_name not in self._prompt_handlers:
                return self._make_error(request_id, ERROR_METHOD_NOT_FOUND, f"Prompt not found: {prompt_name}")
            try:
                result = await self._prompt_handlers[prompt_name](**arguments)
                return self._make_response(request_id, result)
            except Exception as e:
                return self._make_error(request_id, ERROR_INTERNAL, str(e))

        if method is not None and method.startswith("notifications/"):
            return self._make_response(request_id, {})

        return self._make_error(request_id, ERROR_METHOD_NOT_FOUND, f"Method not found: {method}")

    async def start(self) -> None:
        self._running = True
        logger.info("mcp_server_started", name=self.name, version=self.version)
        while self._running:
            raw = await self._read_queue.get()
            if raw is None:
                break
            response = await self.handle_request(raw)
            await self._write_queue.put(response)

    async def stop(self) -> None:
        self._running = False
        await self._read_queue.put(None)
        logger.info("mcp_server_stopped", name=self.name)

    def list_tools(self) -> list[dict[str, Any]]:
        return list(self._tools.values())

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tool_handlers:
            raise MCPError(ERROR_METHOD_NOT_FOUND, f"Tool not found: {name}")
        return await self._tool_handlers[name](**arguments)

    def list_resources(self) -> list[dict[str, Any]]:
        return list(self._resources.values())

    async def read_resource(self, uri: str) -> Any:
        if uri not in self._resource_handlers:
            raise MCPError(ERROR_METHOD_NOT_FOUND, f"Resource not found: {uri}")
        return await self._resource_handlers[uri](uri)

    def list_prompts(self) -> list[dict[str, Any]]:
        return list(self._prompts.values())

    async def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if name not in self._prompt_handlers:
            raise MCPError(ERROR_METHOD_NOT_FOUND, f"Prompt not found: {name}")
        return await self._prompt_handlers[name](**(arguments or {}))
