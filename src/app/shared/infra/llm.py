"""Ollama chat client; with ``OLLAMA_URL`` empty every call fails with ``ServiceUnavailableError`` (503)."""

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx
from dishka import Provider, Scope, provide

from app.shared.application.exceptions import ServiceUnavailableError
from app.shared.application.ports.llm import LlmClient, LlmMessage
from app.shared.infra.config import LlmConfig


def _messages(messages: list[LlmMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


class OllamaClient(LlmClient):
    """``POST /api/chat``. The semaphore caps parallel generations: one GPU serves only a few at once."""

    def __init__(self, http: httpx.AsyncClient, model: str, max_concurrency: int) -> None:
        self._http = http
        self._model = model
        self._slots = asyncio.Semaphore(max_concurrency)

    async def complete(self, messages: list[LlmMessage], *, json_schema: Mapping[str, Any] | None = None) -> str:
        body: dict[str, Any] = {"model": self._model, "messages": _messages(messages), "stream": False}
        if json_schema is not None:
            body["format"] = dict(json_schema)
        async with self._slots:
            try:
                response = await self._http.post("/api/chat", json=body)
                response.raise_for_status()
                content: str = response.json()["message"]["content"]
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise ServiceUnavailableError("LLM request failed") from exc
        return content

    async def stream(self, messages: list[LlmMessage]) -> AsyncIterator[str]:
        body = {"model": self._model, "messages": _messages(messages), "stream": True}
        async with self._slots:
            try:
                async with self._http.stream("POST", "/api/chat", json=body) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        if text := chunk.get("message", {}).get("content"):
                            yield text
                        if chunk.get("done"):
                            return
            except (httpx.HTTPError, ValueError) as exc:
                raise ServiceUnavailableError("LLM request failed") from exc


class DisabledLlm(LlmClient):
    async def complete(self, messages: list[LlmMessage], *, json_schema: Mapping[str, Any] | None = None) -> str:
        raise ServiceUnavailableError("LLM is not configured: set OLLAMA_URL")

    async def stream(self, messages: list[LlmMessage]) -> AsyncIterator[str]:
        raise ServiceUnavailableError("LLM is not configured: set OLLAMA_URL")
        yield ""  # pragma: no cover -- makes this an async generator


class LlmProvider(Provider):
    scope = Scope.APP

    @provide
    async def llm(self, config: LlmConfig) -> AsyncIterator[LlmClient]:
        if not config.ollama_url:
            yield DisabledLlm()
            return
        async with httpx.AsyncClient(base_url=config.ollama_url, timeout=config.timeout) as http:
            yield OllamaClient(http, config.model, config.max_concurrency)
