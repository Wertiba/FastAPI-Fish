from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.exceptions.base import RepositoryError
from app.core.schemas.experiment import ExperimentStatus
from app.infrastructure.models import Decision, Experiment, Variant
from app.infrastructure.repositories import BaseRepository


class DecisionRepository(BaseRepository[Decision]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=Decision)

    async def get_by_user_and_flag(self, user_id: UUID, flag_code: str) -> Decision:
        stmt = (
            select(Decision)
            .join(Decision.variant) # noqa
            .join(Variant.experiment)   # noqa
            .where(and_(
                Experiment.flag_code == flag_code,  # noqa
                Experiment.status.in_([ExperimentStatus.RUNNING, ExperimentStatus.ROLLBACK]),  # noqa
                Experiment.isCurrent == True,   # noqa
                Decision.user_id == user_id,    # noqa
            ))
            .options(
                selectinload(Decision.variant).selectinload(Variant.experiment).selectinload(Experiment.variants) # noqa
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_variant(self, id_: UUID) -> Decision | None:
        try:
            stmt = select(Decision).where(Decision.id == id_).options(
                selectinload(Decision.variant).selectinload(Variant.experiment)) # noqa
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_experiment(self, experiment_id: UUID) -> list[Decision]:
        stmt = (
            select(Decision)
            .join(Decision.variant)
            .where(Variant.experiment_id == experiment_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
