"""External-system adapters against fakes of the systems themselves (httpx.MockTransport, a temp dir)."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.shared.application.exceptions import ServiceUnavailableError
from app.shared.application.ports.llm import LlmMessage
from app.shared.application.ports.messaging import PushMessage
from app.shared.infra.cache import InMemoryCache, InMemoryLock
from app.shared.infra.llm import DisabledLlm, OllamaClient
from app.shared.infra.push import FcmPushSender
from app.shared.infra.storage import LocalFileStorage

QUESTION = [LlmMessage(role="user", content="hi")]


async def test_in_memory_cache_expires() -> None:
    cache = InMemoryCache()
    await cache.set("k", b"v", timedelta(minutes=1))
    assert await cache.get("k") == b"v"
    await cache.set("gone", b"v", timedelta(seconds=-1))
    assert await cache.get("gone") is None
    await cache.delete("k")
    assert await cache.get("k") is None


async def test_in_memory_lock_excludes_and_releases() -> None:
    lock = InMemoryLock()
    async with lock.acquire("a", timedelta(minutes=1)) as first:
        async with lock.acquire("a", timedelta(minutes=1)) as second:
            assert (first, second) == (True, False)
    async with lock.acquire("a", timedelta(minutes=1)) as again:
        assert again


async def test_local_storage(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    await storage.upload("pets/1/avatar.jpg", b"img", "image/jpeg")
    assert await storage.download("pets/1/avatar.jpg") == b"img"
    await storage.delete("pets/1/avatar.jpg")
    await storage.delete("pets/1/avatar.jpg")  # idempotent
    with pytest.raises(FileNotFoundError):
        await storage.download("pets/1/avatar.jpg")
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.upload("../escape", b"", "text/plain")
    with pytest.raises(ServiceUnavailableError):
        await storage.upload_url("k", "image/jpeg", timedelta(minutes=5))


def ollama(handler: Any) -> OllamaClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ollama")
    return OllamaClient(http, model="test-model", max_concurrency=1)


async def test_ollama_complete_passes_schema() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"role": "assistant", "content": '{"ok": true}'}})

    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    assert await ollama(handler).complete(QUESTION, json_schema=schema) == '{"ok": true}'
    assert seen["model"] == "test-model"
    assert seen["format"] == schema
    assert seen["stream"] is False


async def test_ollama_stream() -> None:
    lines = [{"message": {"content": "При"}}, {"message": {"content": "вет"}}, {"done": True}]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content="\n".join(json.dumps(line) for line in lines).encode())

    assert [chunk async for chunk in ollama(handler).stream(QUESTION)] == ["При", "вет"]


async def test_ollama_errors_are_unavailable() -> None:
    with pytest.raises(ServiceUnavailableError):
        await ollama(lambda request: httpx.Response(500)).complete(QUESTION)
    with pytest.raises(ServiceUnavailableError):
        await DisabledLlm().complete(QUESTION)
    with pytest.raises(ServiceUnavailableError):
        async for _ in DisabledLlm().stream(QUESTION):
            pass


def service_account() -> dict[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return {
        "project_id": "demo",
        "client_email": "push@demo.iam.gserviceaccount.com",
        "private_key": pem.decode(),
        "token_uri": "https://oauth2.example/token",
    }


async def test_fcm_sends_and_detects_unregistered_tokens() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.host == "oauth2.example":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer t"
        token = json.loads(request.content)["message"]["token"]
        if token == "stale":
            return httpx.Response(404, json={"error": {"details": [{"errorCode": "UNREGISTERED"}]}})
        return httpx.Response(200, json={"name": "projects/demo/messages/1"})

    sender = FcmPushSender(httpx.AsyncClient(transport=httpx.MockTransport(handler)), service_account())
    message = PushMessage(title="Барсик", body="Пора кормить", data={"pet_id": "1"})

    assert await sender.send("fresh", message) is True
    assert await sender.send("stale", message) is False
    assert calls.count("/token") == 1  # the access token is cached
