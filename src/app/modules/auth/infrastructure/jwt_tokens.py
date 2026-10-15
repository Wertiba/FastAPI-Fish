import hashlib
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from app.modules.auth.application.ports import TokenService
from app.modules.auth.config import AuthConfig
from app.shared.domain.errors import AuthenticationError
from app.shared.domain.time import utc_now

ACCESS = "access"
REFRESH = "refresh"


class JwtTokenService(TokenService):
    def __init__(self, config: AuthConfig) -> None:
        self._config = config

    @property
    def access_ttl(self) -> int:
        return self._config.access_ttl_seconds

    @property
    def refresh_ttl(self) -> int:
        return self._config.refresh_ttl_seconds

    def create_access_token(self, user_id: UUID) -> str:
        return self._encode(user_id, ACCESS, self.access_ttl)

    def create_refresh_token(self, user_id: UUID) -> str:
        return self._encode(user_id, REFRESH, self.refresh_ttl)

    def read_access_token(self, token: str) -> UUID:
        return self._decode(token, ACCESS)

    def read_refresh_token(self, token: str) -> UUID:
        return self._decode(token, REFRESH)

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _encode(self, user_id: UUID, token_type: str, ttl: int) -> str:
        now = utc_now()
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "type": token_type,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(seconds=ttl),
        }
        return jwt.encode(payload, self._config.jwt_secret, algorithm=self._config.jwt_algorithm)

    def _decode(self, token: str, expected_type: str) -> UUID:
        try:
            payload = jwt.decode(
                token,
                self._config.jwt_secret,
                algorithms=[self._config.jwt_algorithm],
                options={"require": ["sub", "exp", "type"]},
            )
            if payload["type"] != expected_type:
                raise AuthenticationError
            return UUID(payload["sub"])
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise AuthenticationError from exc
