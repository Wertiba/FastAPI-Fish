from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.entrypoints import bot
from app.run import PROCESSES, parse_args
from app.shared.application.exceptions import ServiceUnavailableError
from app.shared.presentation.http.middleware.app_version import is_older, parse_version


def test_run_knows_every_process() -> None:
    assert parse_args([]).process == "api"
    for process in PROCESSES:
        assert parse_args([process]).process == process
    with pytest.raises(SystemExit):
        parse_args(["nope"])


async def test_bot_refuses_to_start_without_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="TELEGRAM_BOT_TOKEN"):
        await bot.main()


def test_bot_dispatcher_has_the_common_commands() -> None:
    dispatcher = bot.build_dispatcher()
    assert [router.name for router in dispatcher.sub_routers][-1] == "common"


def test_versions() -> None:
    assert parse_version("2.14.1") == (2, 14, 1)
    assert parse_version("beta") is None
    assert is_older((2, 9), (2, 10, 0))
    assert not is_older((2, 10), (2, 10, 0))


@pytest.fixture
def app_with(make_app: Callable[..., FastAPI], monkeypatch: pytest.MonkeyPatch) -> Callable[..., TestClient]:
    def _make(**env: str) -> TestClient:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        app = make_app()

        async def unavailable() -> Any:
            raise ServiceUnavailableError("LLM is down")

        app.add_api_route("/test/unavailable", unavailable)
        return TestClient(app, base_url="https://testserver")

    return _make


def test_old_mobile_app_must_update(app_with: Callable[..., TestClient]) -> None:
    with app_with(MOBILE_MIN_APP_VERSION="2.0") as client:
        old = client.get("/health/liveness", headers={"X-App-Version": "1.9.3"})
        assert old.status_code == 426
        assert old.json()["code"] == "APP_UPDATE_REQUIRED"
        assert client.get("/health/liveness", headers={"X-App-Version": "2.0.0"}).status_code == 200
        assert client.get("/health/liveness").status_code == 200  # the website sends no version


def test_unavailable_dependency_is_503(app_with: Callable[..., TestClient]) -> None:
    with app_with() as client:
        response = client.get("/test/unavailable")
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"


def test_log_fields_do_not_shadow_log_record_attributes() -> None:
    """``extra={"process": ...}`` raises KeyError: ``process`` is a built-in LogRecord attribute (the PID)."""
    import logging

    from app.shared.infra.logger import _FIELDS, _UUID_FIELDS

    builtins = set(vars(logging.LogRecord("x", logging.INFO, "", 0, "", None, None)))
    assert not (_FIELDS | _UUID_FIELDS) & builtins
