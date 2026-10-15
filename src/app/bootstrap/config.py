"""Все настройки приложения в одном месте. Источник — переменные окружения и ``.env``.

Модули не читают ``Settings`` напрямую: composition root (``bootstrap/ioc.py``)
собирает из него маленькие конфиги модулей (``AuthConfig``, ``DatabaseConfig``…).
"""

import re
from functools import cached_property

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DURATION = re.compile(r"^(\d+)([smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(value: str) -> int:
    """``"15m"`` -> 900, ``"30d"`` -> 2592000."""
    match = _DURATION.match(value.strip())
    if not match:
        raise ValueError(f"Invalid duration {value!r}, expected e.g. '15m', '30d'")
    amount, unit = match.groups()
    return int(amount) * _UNIT_SECONDS[unit]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        validate_by_name=True,
        validate_by_alias=True,
    )

    # --- app
    host: str = Field("0.0.0.0", alias="APP_HOST")  # noqa: S104
    port: int = Field(8080, alias="APP_PORT")
    cors_allowed_origins: str = Field(
        "http://localhost,http://localhost:8080", alias="APP_CORS_ALLOWED_ORIGINS"
    )
    cookie_secure: bool = Field(True, alias="APP_COOKIE_SECURE")

    # --- database
    db_host: str = Field("localhost", alias="DB_HOST")
    db_port: int = Field(5432, alias="DB_PORT")
    db_name: str = Field("app", alias="DB_NAME")
    db_user: str = Field("postgres", alias="DB_USER")
    db_password: str = Field("", alias="DB_PASSWORD")
    db_url_override: str | None = Field(None, alias="DB_URL")
    db_echo: bool = Field(False, alias="DB_ECHO")
    db_pool_size: int = Field(20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(10, alias="DB_MAX_OVERFLOW")
    db_create_tables: bool = Field(False, alias="DB_CREATE_TABLES")

    # --- security
    jwt_secret: str = Field(alias="APP_SECURITY_JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="APP_SECURITY_JWT_ALGORITHM")
    access_token_expiration: str = Field("15m", alias="APP_SECURITY_ACCESS_TOKEN_EXPIRATION")
    refresh_token_expiration: str = Field("30d", alias="APP_SECURITY_REFRESH_TOKEN_EXPIRATION")

    # --- bootstrap admin (создаётся при старте, если задан email)
    admin_email: str | None = Field(None, alias="APP_ADMIN_EMAIL")
    admin_password: str | None = Field(None, alias="APP_ADMIN_PASSWORD")
    admin_full_name: str = Field("Admin Admin", alias="APP_ADMIN_FULLNAME")

    # --- logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_file: str = Field("logs/app.log", alias="LOG_FILE")  # пусто = без файла

    @field_validator("access_token_expiration", "refresh_token_expiration")
    @classmethod
    def _validate_duration(cls, value: str) -> str:
        parse_duration(value)
        return value

    @cached_property
    def database_url(self) -> str:
        if self.db_url_override:
            return self.db_url_override
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]
