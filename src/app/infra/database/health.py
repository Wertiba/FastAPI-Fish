from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.database_health import DatabaseHealth


class SqlAlchemyDatabaseHealth(DatabaseHealth):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check(self) -> None:
        await self.session.execute(text("SELECT 1"))
