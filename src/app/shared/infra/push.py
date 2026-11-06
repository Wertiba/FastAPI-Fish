"""Push notifications through FCM HTTP v1; only logged when ``FCM_SERVICE_ACCOUNT_FILE`` is empty.

The service account JSON comes from Firebase console -> Project settings -> Service accounts.
iOS devices are reached through FCM as well (upload the APNs key to Firebase).
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import jwt
from dishka import Provider, Scope, provide

from app.shared.application.exceptions import ServiceUnavailableError
from app.shared.application.ports.messaging import PushMessage, PushSender
from app.shared.infra.config import PushConfig

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_UNREGISTERED = {"UNREGISTERED", "INVALID_ARGUMENT"}


class FcmPushSender(PushSender):
    def __init__(self, http: httpx.AsyncClient, service_account: dict[str, Any]) -> None:
        self._http = http
        self._account = service_account
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def _access_token(self) -> str:
        if self._token is not None and time.time() < self._token_expires_at - 60:
            return self._token
        now = int(time.time())
        token_uri = self._account.get("token_uri", "https://oauth2.googleapis.com/token")
        assertion = jwt.encode(
            {"iss": self._account["client_email"], "scope": _SCOPE, "aud": token_uri, "iat": now, "exp": now + 3600},
            self._account["private_key"],
            algorithm="RS256",
        )
        response = await self._http.post(
            token_uri,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        )
        response.raise_for_status()
        data = response.json()
        self._token, self._token_expires_at = data["access_token"], now + int(data.get("expires_in", 3600))
        return self._token

    async def send(self, device_token: str, message: PushMessage) -> bool:
        url = f"https://fcm.googleapis.com/v1/projects/{self._account['project_id']}/messages:send"
        body = {
            "message": {
                "token": device_token,
                "notification": {"title": message.title, "body": message.body},
                "data": dict(message.data),
            }
        }
        try:
            response = await self._http.post(
                url, json=body, headers={"Authorization": f"Bearer {await self._access_token()}"}
            )
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("FCM request failed") from exc
        if response.status_code in {400, 404}:
            details = response.json().get("error", {}).get("details", [])
            if any(detail.get("errorCode") in _UNREGISTERED for detail in details):
                return False
        if response.is_error:
            raise ServiceUnavailableError(f"FCM answered {response.status_code}")
        return True


class LogPushSender(PushSender):
    """Development: logs that a push would be sent (never its content)."""

    async def send(self, device_token: str, message: PushMessage) -> bool:
        logger.info("push_skipped")
        return True


class PushProvider(Provider):
    scope = Scope.APP

    @provide
    async def sender(self, config: PushConfig) -> AsyncIterator[PushSender]:
        if not config.fcm_service_account_file:
            yield LogPushSender()
            return
        account = json.loads(Path(config.fcm_service_account_file).read_text(encoding="utf-8"))
        async with httpx.AsyncClient(timeout=10) as http:
            yield FcmPushSender(http, account)
