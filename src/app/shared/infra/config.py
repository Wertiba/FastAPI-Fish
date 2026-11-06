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


# ---------------------------------------------------------------- external systems
# Every one is optional: an empty address switches to a local fallback, so the template starts with
# Postgres alone and the tests need nothing. Set the address and the real adapter is used.


class KafkaConfig(BaseModel):
    """Empty ``bootstrap_servers``: the worker delivers outbox messages to local consumers itself."""

    bootstrap_servers: str = Field(alias="KAFKA_BOOTSTRAP_SERVERS", default="")
    client_id: str = Field(alias="KAFKA_CLIENT_ID", default="app")
    group_id: str = Field(alias="KAFKA_GROUP_ID", default="app")


class WorkerConfig(BaseModel):
    outbox_poll_interval: float = Field(alias="WORKER_OUTBOX_POLL_INTERVAL", default=1.0, gt=0)
    outbox_batch_size: int = Field(alias="WORKER_OUTBOX_BATCH_SIZE", default=100, ge=1)


class RedisConfig(BaseModel):
    """Empty ``url``: in-process cache and locks (fine for one instance of each process)."""

    url: str = Field(alias="REDIS_URL", default="", repr=False)


class StorageConfig(BaseModel):
    """Empty ``bucket``: files go to ``local_dir`` (development only, no presigned URLs for clients)."""

    bucket: str = Field(alias="S3_BUCKET", default="")
    endpoint_url: str | None = Field(alias="S3_ENDPOINT_URL", default=None)
    region: str = Field(alias="S3_REGION", default="us-east-1")
    access_key: str | None = Field(alias="S3_ACCESS_KEY", default=None, repr=False)
    secret_key: str | None = Field(alias="S3_SECRET_KEY", default=None, repr=False)
    local_dir: str = Field(alias="STORAGE_LOCAL_DIR", default=".storage")


class LlmConfig(BaseModel):
    """Empty ``ollama_url``: LLM calls fail with ``ServiceUnavailableError`` (503), the rest works."""

    ollama_url: str = Field(alias="OLLAMA_URL", default="")
    model: str = Field(alias="OLLAMA_MODEL", default="qwen2.5:7b")
    timeout: float = Field(alias="OLLAMA_TIMEOUT", default=120.0, gt=0)
    max_concurrency: int = Field(alias="OLLAMA_MAX_CONCURRENCY", default=2, ge=1)


class TelegramConfig(BaseModel):
    """Empty ``bot_token``: outgoing messages are only logged and the ``bot`` process refuses to start."""

    bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN", default="", repr=False)


class PushConfig(BaseModel):
    """Empty ``fcm_service_account_file``: pushes are only logged."""

    fcm_service_account_file: str = Field(alias="FCM_SERVICE_ACCOUNT_FILE", default="")


class MobileConfig(BaseModel):
    """Clients sending ``X-App-Version`` below this get 426; empty disables the check."""

    min_app_version: str = Field(alias="MOBILE_MIN_APP_VERSION", default="", pattern=r"^(\d+(\.\d+)*)?$")


def build_database_url(config: DatabaseConfig) -> URL:
    return URL.create(
        config.driver,
        username=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.name,
    )
