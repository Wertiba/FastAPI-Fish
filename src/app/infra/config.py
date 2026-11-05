import socket
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.engine import URL


class RunConfig(BaseModel):
    host: str = Field(alias="RUN_HOST", default="0.0.0.0")  # noqa: S104 -- API listen address
    port: int = Field(alias="RUN_PORT", default=8080)


class DatabaseConfig(BaseModel):
    host: str = Field(alias="DB_HOST")
    name: str = Field(alias="DB_NAME")
    user: str = Field(alias="DB_USER")
    password: str = Field(alias="DB_PASSWORD", repr=False)
    port: int = Field(alias="DB_PORT", default=5432)
    driver: str = Field(alias="DB_DRIVER", default="postgresql+asyncpg")
    pool_size: int = Field(alias="DB_POOL_SIZE", default=20)
    max_overflow: int = Field(alias="DB_MAX_OVERFLOW", default=10)


class SecurityConfig(BaseModel):
    jwt_secret: str = Field(alias="APP_SECURITY_JWT_SECRET", repr=False)
    access_token_expiration: str = Field(alias="APP_SECURITY_ACCESS_TOKEN_EXPIRATION", default="15m")
    refresh_token_expiration: str = Field(alias="APP_SECURITY_REFRESH_TOKEN_EXPIRATION", default="30d")
    algorithm: str = Field(alias="APP_SECURITY_ALGORITHM", default="HS256")


class AdminConfig(BaseModel):
    """Admin created on startup when both email and password are set; skipped if the email is taken."""

    email: str | None = Field(alias="ADMIN_EMAIL", default=None)
    password: str | None = Field(alias="ADMIN_PASSWORD", default=None, repr=False)
    full_name: str = Field(alias="ADMIN_FULL_NAME", default="Admin Admin")


class HttpConfig(BaseModel):
    cookie_secure: bool = Field(alias="APP_COOKIE_SECURE", default=True)
    cors_allowed_origins: str = Field(
        alias="APP_CORS_ALLOWED_ORIGINS", default="http://localhost,http://localhost:8080"
    )


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(alias="LOG_CONSOLE_LEVEL", default="INFO")
    env: str = Field(alias="LOG_ENV", default="dev", pattern=r"^[a-z][a-z0-9_-]*$", validate_default=True)
    system: str = Field(alias="LOG_SYSTEM", default="app", pattern=r"^[a-z][a-z0-9_-]*$", validate_default=True)
    inst: str = Field(
        alias="LOG_INST",
        default_factory=socket.gethostname,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$",
        validate_default=True,
    )


def build_database_url(config: DatabaseConfig) -> URL:
    return URL.create(
        config.driver,
        username=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.name,
    )
