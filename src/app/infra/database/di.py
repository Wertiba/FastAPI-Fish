from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.database_health import DatabaseHealth
from app.application.ports.unit_of_work import UnitOfWork
from app.infra.config import DatabaseConfig, build_database_url
from app.infra.database.db_helper import DatabaseHelper
from app.infra.database.health import SqlAlchemyDatabaseHealth
from app.infra.database.unit_of_work import SqlAlchemyUnitOfWork


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def database(self, config: DatabaseConfig) -> AsyncIterator[DatabaseHelper]:
        database = DatabaseHelper(
            url=build_database_url(config),
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
        )
        try:
            yield database
        finally:
            await database.dispose()

    @provide(scope=Scope.REQUEST)
    async def session(self, database: DatabaseHelper) -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            try:
                yield session
            finally:
                if session.in_transaction():
                    await session.rollback()

    unit_of_work = provide(SqlAlchemyUnitOfWork, provides=UnitOfWork, scope=Scope.REQUEST)
    health = provide(SqlAlchemyDatabaseHealth, provides=DatabaseHealth, scope=Scope.REQUEST)
