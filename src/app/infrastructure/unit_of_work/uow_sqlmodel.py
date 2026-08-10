from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import UserRepository
from app.infrastructure.unit_of_work.abstract_uow import AbstractUnitOfWork


class UnitOfWork(AbstractUnitOfWork):
    user_repo: UserRepository

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        self.user_repo = UserRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()
