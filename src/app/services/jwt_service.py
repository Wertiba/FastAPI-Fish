import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext

import jwt

from app.core.config import settings
from app.core.exceptions.user_exs import InvalidCredentialsError
from app.core.utils import Singleton, parse_duration_seconds

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class JWTService(Singleton):
    def __init__(self):
        self.pwd_context = CryptContext(schemes=[settings.token.SCHEMA], deprecated="auto")
        self.secret_key = settings.APP_SECURITY_JWT_SECRET
        self.algorithm = settings.token.access_token.ALGORITHM
        self.access_expire_seconds = parse_duration_seconds(settings.APP_SECURITY_ACCESS_TOKEN_EXPIRATION)
        self.refresh_expire_seconds = parse_duration_seconds(settings.APP_SECURITY_REFRESH_TOKEN_EXPIRATION)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

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

    def decode_token(self, token: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.InvalidTokenError as e:
            raise InvalidCredentialsError from e

        if payload.get("sub") is None or payload.get("type") != expected_type:
            raise InvalidCredentialsError
        return payload

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
