import hashlib
import uuid
from typing import Any

import jwt

from app.modules.auth.application.ports import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TokenService
from app.shared.domain.errors import InvalidCredentialsError
from app.shared.domain.time import TimeService
from app.shared.infra.config import SecurityConfig


class JWTService(TokenService):
    """``iat`` and ``exp`` follow ``TimeService``, so a frozen test clock moves tokens too."""

    def __init__(self, config: SecurityConfig, time: TimeService) -> None:
        self.time = time
        self.secret_key = config.jwt_secret
        self.algorithm = config.algorithm
        self.access_expire_seconds = int(time.parse_duration(config.access_token_expiration).total_seconds())
        self.refresh_expire_seconds = int(time.parse_duration(config.refresh_token_expiration).total_seconds())

    def _create_token(self, subject: str, token_type: str, expire_seconds: int) -> str:
        now = self.time.now()
        payload = {
            "sub": subject,
            "type": token_type,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + expire_seconds,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, subject: str) -> str:
        return self._create_token(subject, ACCESS_TOKEN_TYPE, self.access_expire_seconds)

    def create_refresh_token(self, subject: str) -> str:
        return self._create_token(subject, REFRESH_TOKEN_TYPE, self.refresh_expire_seconds)

    def decode_token(self, token: str, expected_type: str) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                # Expiry is checked below against TimeService, not against PyJWT's system clock.
                options={"require": ["sub", "exp", "type"], "verify_exp": False, "verify_iat": False},
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidCredentialsError from exc

        expires = payload["exp"]
        if not isinstance(expires, int | float) or isinstance(expires, bool) or expires <= self.time.now().timestamp():
            raise InvalidCredentialsError

        if payload.get("type") != expected_type:
            raise InvalidCredentialsError
        return payload

    def hash_token(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
