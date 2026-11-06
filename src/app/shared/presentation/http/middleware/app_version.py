"""Minimum supported mobile app version.

Web clients do not send ``X-App-Version`` and are never blocked. A mobile build sends its version;
below ``MOBILE_MIN_APP_VERSION`` it gets 426 ``APP_UPDATE_REQUIRED`` and shows "please update".
Old builds live for years, so keep ``/api/v1`` compatible and raise the minimum only for real breaks.
"""

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.shared.presentation.http.errors import UpgradeRequired

APP_VERSION_HEADER = "X-App-Version"


def parse_version(value: str) -> tuple[int, ...] | None:
    """``"2.14.1"`` -> ``(2, 14, 1)``; ``None`` for anything else (such clients are let through)."""
    parts = value.strip().split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def is_older(version: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    width = max(len(version), len(minimum))
    return version + (0,) * (width - len(version)) < minimum + (0,) * (width - len(minimum))


class AppVersionMiddleware:
    def __init__(self, app: ASGIApp, min_version: str) -> None:
        self.app = app
        self.minimum = parse_version(min_version) if min_version else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.minimum is not None:
            version = parse_version(Headers(scope=scope).get(APP_VERSION_HEADER, ""))
            if version is not None and is_older(version, self.minimum):
                api_exc = UpgradeRequired(path=scope.get("path", ""))
                response = JSONResponse(
                    status_code=api_exc.status_code,
                    content=api_exc.to_response().model_dump(exclude_none=True, mode="json"),
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
