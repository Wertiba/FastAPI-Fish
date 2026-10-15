"""Composition root: здесь (и только здесь) всё собирается в один контейнер Dishka."""

from collections.abc import AsyncIterable, Sequence

from dishka import AsyncContainer, Provider, Scope, from_context, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.bootstrap.config import Settings, parse_duration
from app.modules.auth.config import AuthConfig
from app.shared.application.events import EventPublisher
from app.shared.application.transaction import TransactionManager
from app.shared.infrastructure.database import DatabaseConfig, create_engine, create_session_maker
from app.shared.infrastructure.event_bus import EventRegistry, InProcessEventBus
from app.shared.infrastructure.transaction import SqlTransactionManager
from app.shared.module import Module


class ConfigProvider(Provider):
    """``Settings`` -> маленькие конфиги модулей. Модули не видят ``Settings`` целиком."""

    scope = Scope.APP
    settings = from_context(provides=Settings)

    @provide
    def database(self, s: Settings) -> DatabaseConfig:
        return DatabaseConfig(
            url=s.database_url,
            echo=s.db_echo,
            pool_size=s.db_pool_size,
            max_overflow=s.db_max_overflow,
        )

    @provide
    def auth(self, s: Settings) -> AuthConfig:
        return AuthConfig(
            jwt_secret=s.jwt_secret,
            jwt_algorithm=s.jwt_algorithm,
            access_ttl_seconds=parse_duration(s.access_token_expiration),
            refresh_ttl_seconds=parse_duration(s.refresh_token_expiration),
            cookie_secure=s.cookie_secure,
        )


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def engine(self, config: DatabaseConfig) -> AsyncIterable[AsyncEngine]:
        engine = create_engine(config)
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_maker(engine)

    @provide(scope=Scope.REQUEST)
    async def session(self, maker: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        async with maker() as session:  # без commit() всё откатится при выходе
            yield session

    transaction = provide(SqlTransactionManager, provides=TransactionManager, scope=Scope.REQUEST)


class EventsProvider(Provider):
    registry = from_context(provides=EventRegistry, scope=Scope.APP)
    publisher = provide(InProcessEventBus, provides=EventPublisher, scope=Scope.REQUEST)


def build_event_registry(modules: Sequence[Module]) -> EventRegistry:
    registry = EventRegistry()
    for module in modules:
        for event_type, handlers in module.subscriptions.items():
            for handler in handlers:
                registry.subscribe(event_type, handler)
    return registry


def build_container(settings: Settings, modules: Sequence[Module]) -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        EventsProvider(),
        FastapiProvider(),
        *(provider for module in modules for provider in module.providers),
        context={Settings: settings, EventRegistry: build_event_registry(modules)},
    )
