from collections.abc import Callable
from os import environ as env

from dishka import Provider, Scope, provide
from pydantic import BaseModel

from app.shared.domain.time import TimeService
from app.shared.infra.config import (
    AdminConfig,
    DatabaseConfig,
    HttpConfig,
    KafkaConfig,
    LlmConfig,
    LoggingConfig,
    MobileConfig,
    PushConfig,
    RedisConfig,
    RunConfig,
    SecurityConfig,
    StorageConfig,
    TelegramConfig,
    WorkerConfig,
)
from app.shared.infra.logger import Logger

CONFIGS: tuple[type[BaseModel], ...] = (
    RunConfig,
    DatabaseConfig,
    SecurityConfig,
    AdminConfig,
    HttpConfig,
    LoggingConfig,
    KafkaConfig,
    WorkerConfig,
    RedisConfig,
    StorageConfig,
    LlmConfig,
    TelegramConfig,
    PushConfig,
    MobileConfig,
)


def _from_env[C: BaseModel](config_cls: type[C]) -> Callable[[], C]:
    def read() -> C:
        return config_cls.model_validate(env)

    return read


class ConfigProvider(Provider):
    """Configs are read from the process environment only; ``.env`` is loaded by the launcher."""

    scope = Scope.APP

    def __init__(self) -> None:
        super().__init__()
        for config_cls in CONFIGS:
            self.provide(_from_env(config_cls), provides=config_cls)

    logger = provide(Logger)
    time = provide(TimeService)
