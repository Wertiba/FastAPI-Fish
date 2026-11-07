from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.application.exceptions import ApplicationError, DuplicateError
from app.shared.application.ports.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entity: object) -> None:
        self.session.add(entity)

    async def delete(self, entity: object) -> None:
        try:
            await self.session.delete(entity)
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def flush(self) -> None:
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise DuplicateError("Unique field already exists") from exc
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            raise DuplicateError("Unique field already exists") from exc
        except SQLAlchemyError as exc:
            raise ApplicationError("Database error") from exc
