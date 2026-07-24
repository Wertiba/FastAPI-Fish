from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions.base import RepositoryError
from app.infrastructure.models import Flag
from app.infrastructure.repositories.base_repo import BaseRepository


class FlagRepository(BaseRepository[Flag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=Flag)

    async def get_by_code(self, code: str) -> Flag | None:
        try:
            stmt = select(Flag).where(Flag.code == code)  # type: ignore[attr-defined]  # noqa
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e
