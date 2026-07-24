from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions.base import RepositoryError
from app.infrastructure.models import Review
from app.infrastructure.repositories.base_repo import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=Review)

    async def get_by_experiment(self, exp_id: UUID) -> list[Review]:
        try:
            stmt = select(Review).where(Review.experiment_id == exp_id)  # noqa
            res = await self.session.execute(stmt)
            return list(res.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e
