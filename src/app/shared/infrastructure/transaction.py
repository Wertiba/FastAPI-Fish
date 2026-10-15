from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.application.transaction import TransactionManager


class SqlTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def flush(self) -> None:
        await self._session.flush()
