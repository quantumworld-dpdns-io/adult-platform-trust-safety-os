from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int | None = None,
        stream: bool = False,
        format: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        if format is not None:
            payload["format"] = format
        if tools is not None:
            payload["tools"] = tools

        if stream:
            return self._stream_chat(payload)

        response = await self._client.post("/api/chat", json=payload)
        self._raise_for_status(response)
        return response.json()

    async def _stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        payload["stream"] = True
        async with self._client.stream("POST", "/api/chat", json=payload) as response:
            self._raise_for_status(response)
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
                    if data.get("done", False):
                        break

    async def generate(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int | None = None,
        stream: bool = False,
        raw: bool = False,
    ) -> dict[str, Any] | AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "raw": raw,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }
        if system is not None:
            payload["system"] = system
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        if stream:
            return self._stream_generate(payload)

        response = await self._client.post("/api/generate", json=payload)
        self._raise_for_status(response)
        return response.json()

    async def _stream_generate(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        payload["stream"] = True
        async with self._client.stream("POST", "/api/generate", json=payload) as response:
            self._raise_for_status(response)
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done", False):
                        break

    async def list_models(self) -> list[dict[str, Any]]:
        response = await self._client.get("/api/tags")
        self._raise_for_status(response)
        data = response.json()
        return data.get("models", [])

    async def pull_model(self, name: str, *, stream: bool = True) -> AsyncIterator[dict[str, Any]] | dict[str, Any]:
        payload = {"name": name, "stream": stream}

        if stream:
            return self._stream_pull(payload)

        response = await self._client.post("/api/pull", json=payload)
        self._raise_for_status(response)
        return response.json()

    async def _stream_pull(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        async with self._client.stream("POST", "/api/pull", json=payload) as response:
            self._raise_for_status(response)
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)

    async def get_model_info(self, name: str) -> dict[str, Any]:
        payload = {"name": name}
        response = await self._client.post("/api/show", json=payload)
        self._raise_for_status(response)
        return response.json()

    async def embeddings(self, model: str, input: str | list[str]) -> list[list[float]]:
        if isinstance(input, str):
            input = [input]
        payload = {"model": model, "input": input}
        response = await self._client.post("/api/embed", json=payload)
        self._raise_for_status(response)
        data = response.json()
        return data.get("embeddings", [])

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise OllamaError(f"Ollama API error {response.status_code}: {detail}")
