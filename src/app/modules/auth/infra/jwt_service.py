import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.modules.auth.application.ports import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TokenService
from app.shared.domain.errors import InvalidCredentialsError
from app.shared.infra.config import SecurityConfig
from app.shared.infra.duration import parse_duration_seconds


class JWTService(TokenService):
    def __init__(self, config: SecurityConfig) -> None:
        self.secret_key = config.jwt_secret
        self.algorithm = config.algorithm
        self.access_expire_seconds = parse_duration_seconds(config.access_token_expiration)
        self.refresh_expire_seconds = parse_duration_seconds(config.refresh_token_expiration)

    def _create_token(self, subject: str, token_type: str, expire_seconds: int) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "type": token_type,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expire_seconds)).timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, subject: str) -> str:
        return self._create_token(subject, ACCESS_TOKEN_TYPE, self.access_expire_seconds)

    def create_refresh_token(self, subject: str) -> str:
        return self._create_token(subject, REFRESH_TOKEN_TYPE, self.refresh_expire_seconds)

    def decode_token(self, token: str, expected_type: str) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"require": ["sub", "exp", "type"]}
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidCredentialsError from exc

        if payload.get("type") != expected_type:
            raise InvalidCredentialsError
        return payload

    def hash_token(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
