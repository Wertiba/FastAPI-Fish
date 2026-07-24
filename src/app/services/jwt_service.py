from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions.user_exs import InvalidCredentialsError
from app.core.utils import Singleton


class JWTService(Singleton):
    def __init__(self):
        self.pwd_context = CryptContext(schemes=[settings.token.SCHEMA], deprecated="auto")
        self.secret_key = settings.RANDOM_SECRET
        self.algorithm = settings.token.access_token.ALGORITHM
        self.access_expire_minutes = settings.token.access_token.EXPIRE_MINUTES
        self.refresh_expire_days = settings.token.refresh_token.EXPIRE_DAYS

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def _create_token(self, data: dict, expire: datetime, token_type: str) -> str:
        to_encode = data.copy()
        to_encode.update({"exp": expire.timestamp(), "token_type": token_type})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=self.access_expire_minutes))
        return self._create_token(data, expire, token_type="access_token")  # noqa

    def create_refresh_token(self, data: dict) -> str:
        expire = datetime.now(UTC) + timedelta(days=self.refresh_expire_days)
        return self._create_token(data, expire, token_type="refresh_token")  # noqa

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if "sub" not in payload:
                raise InvalidCredentialsError
            return payload
        except jwt.InvalidTokenError:
            raise InvalidCredentialsError from jwt.InvalidTokenError
