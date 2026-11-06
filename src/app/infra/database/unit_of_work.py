from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import ApplicationError, DuplicateError
from app.application.ports.unit_of_work import UnitOfWork
from app.domain.base import Base


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entity: Base) -> None:
        self.session.add(entity)

    async def delete(self, entity: Base) -> None:
        try:
            await self.session.delete(entity)
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            raise DuplicateError("Unique field already exists") from exc
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc
