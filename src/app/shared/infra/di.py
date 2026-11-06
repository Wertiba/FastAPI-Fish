from os import environ as env

from dishka import Provider, Scope, provide

from app.shared.infra.config import AdminConfig, DatabaseConfig, HttpConfig, LoggingConfig, RunConfig, SecurityConfig
from app.shared.infra.logger import Logger


class ConfigProvider(Provider):
    """Configs are read from the process environment only; ``.env`` is loaded by the launcher."""

    scope = Scope.APP

    @provide
    def get_run(self) -> RunConfig:
        return RunConfig.model_validate(env)

    @provide
    def get_database(self) -> DatabaseConfig:
        return DatabaseConfig.model_validate(env)

    @provide
    def get_security(self) -> SecurityConfig:
        return SecurityConfig.model_validate(env)

    @provide
    def get_admin(self) -> AdminConfig:
        return AdminConfig.model_validate(env)

    @provide
    def get_http(self) -> HttpConfig:
        return HttpConfig.model_validate(env)

    @provide
    def get_logging(self) -> LoggingConfig:
        return LoggingConfig.model_validate(env)

    logger = provide(Logger)
