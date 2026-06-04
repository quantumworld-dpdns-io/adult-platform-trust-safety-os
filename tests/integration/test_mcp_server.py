"""Integration tests for the MCP server."""

from __future__ import annotations

import json

import pytest

from src.api.mcp.server import MCPServer, MCPError


pytestmark = [pytest.mark.integration]


@pytest.fixture
def mcp_server():
    server = MCPServer(name="test-mcp", version="1.0.0")

    async def echo_handler(text: str) -> dict:
        return {"echo": text}

    async def add_handler(a: int, b: int) -> dict:
        return {"result": a + b}

    async def failing_handler() -> dict:
        raise ValueError("intentional error")

    server.register_tool(
        name="echo",
        description="Echoes input text",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        handler=echo_handler,
    )
    server.register_tool(
        name="add",
        description="Adds two numbers",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        },
        handler=add_handler,
    )
    server.register_tool(
        name="failing",
        description="Always fails",
        input_schema={"type": "object"},
        handler=failing_handler,
    )

    async def config_handler(uri: str) -> dict:
        return {"name": "trust-safety", "version": "1.0.0"}

    server.register_resource(
        uri="config://app",
        name="App Config",
        description="Application configuration",
        handler=config_handler,
    )

    return server


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    tools = mcp_server.list_tools()
    assert len(tools) == 3
    names = {t["name"] for t in tools}
    assert "echo" in names
    assert "add" in names
    assert "failing" in names


@pytest.mark.asyncio
async def test_call_tool(mcp_server):
    result = await mcp_server.call_tool("echo", {"text": "hello"})
    assert result == {"echo": "hello"}


@pytest.mark.asyncio
async def test_call_tool_add(mcp_server):
    result = await mcp_server.call_tool("add", {"a": 3, "b": 7})
    assert result == {"result": 10}


@pytest.mark.asyncio
async def test_call_tool_not_found(mcp_server):
    with pytest.raises(MCPError) as exc_info:
        await mcp_server.call_tool("nonexistent", {})
    assert exc_info.value.code == -32601


@pytest.mark.asyncio
async def test_call_tool_error(mcp_server):
    with pytest.raises(MCPError) as exc_info:
        await mcp_server.call_tool("failing", {})
    assert exc_info.value.code == -32603


@pytest.mark.asyncio
async def test_list_resources(mcp_server):
    resources = mcp_server.list_resources()
    assert len(resources) == 1
    assert resources[0]["uri"] == "config://app"


@pytest.mark.asyncio
async def test_read_resource(mcp_server):
    result = await mcp_server.read_resource("config://app")
    assert result["name"] == "trust-safety"


@pytest.mark.asyncio
async def test_read_resource_not_found(mcp_server):
    with pytest.raises(MCPError) as exc_info:
        await mcp_server.read_resource("nonexistent://uri")
    assert exc_info.value.code == -32601


@pytest.mark.asyncio
async def test_handle_request_initialize(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == 1
    assert "result" in body
    assert body["result"]["protocolVersion"] == "2024-11-05"
    assert body["result"]["serverInfo"]["name"] == "test-mcp"


@pytest.mark.asyncio
async def test_handle_request_tools_list(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert "result" in body
    assert "tools" in body["result"]
    assert len(body["result"]["tools"]) == 3


@pytest.mark.asyncio
async def test_handle_request_tools_call(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"text": "test"}},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert "result" in body
    assert "content" in body["result"]


@pytest.mark.asyncio
async def test_handle_request_tools_call_not_found(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert "error" in body
    assert body["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_handle_request_resources_list(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "resources/list",
        "params": {},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert "result" in body
    assert "resources" in body["result"]


@pytest.mark.asyncio
async def test_handle_request_resources_read(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "resources/read",
        "params": {"uri": "config://app"},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert "result" in body
    assert "contents" in body["result"]


@pytest.mark.asyncio
async def test_handle_request_ping(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "ping",
        "params": {},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert body["result"] == {}


@pytest.mark.asyncio
async def test_handle_request_invalid_json(mcp_server):
    response = await mcp_server.handle_request("not json")
    body = json.loads(response)
    assert "error" in body
    assert body["error"]["code"] == -32700


@pytest.mark.asyncio
async def test_handle_request_method_not_found(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 8,
        "method": "unknown/method",
        "params": {},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert "error" in body
    assert body["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_handle_request_notifications(mcp_server):
    request = json.dumps({
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    })
    response = await mcp_server.handle_request(request)
    body = json.loads(response)
    assert body["result"] == {}


@pytest.mark.asyncio
async def test_list_prompts(mcp_server):
    prompts = mcp_server.list_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) == 0
