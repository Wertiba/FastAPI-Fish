from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import and_, select, update

from app.core.exceptions.base import RepositoryError
from app.core.schemas.experiment import ExperimentStatus
from app.infrastructure.models import Experiment, Metric, Variant
from app.infrastructure.repositories import BaseRepository


class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=Experiment)

    async def add_variant(self, variant_data: Variant) -> Variant:
        try:
            self.session.add(variant_data)
            await self.session.flush()
            await self.session.refresh(variant_data)
            return variant_data
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def add_metric(self, metric_data: Metric) -> Metric:
        try:
            self.session.add(metric_data)
            await self.session.flush()
            await self.session.refresh(metric_data)
            return metric_data
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_id_with_variants(self, experiment_id: UUID) -> Experiment | None:
        try:
            result = await self.session.execute(
                select(Experiment)
                .options(selectinload(Experiment.variants)) # noqa
                .where(Experiment.id == experiment_id)  # noqa
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_code(self, code: str, version: float | None = None) -> Experiment | None:
        try:
            stmt = (
                select(Experiment)
                .options(selectinload(Experiment.variants)) # noqa
                .options(selectinload(Experiment.creator))  # noqa
                .options(selectinload(Experiment.reviews))  # noqa
                .options(selectinload(Experiment.metrics))  # noqa
                .options(selectinload(Experiment.metrics).selectinload(Metric.metric_catalog))  # noqa
                .where(Experiment.code == code)  # noqa
            )
            stmt = stmt.where(Experiment.version == version) if version is not None\
                else stmt.where(Experiment.isCurrent == True)    # noqa

            result = await self.session.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_history(self, code: str) -> list[Experiment] | None:
        try:
            result = await self.session.execute(
                select(Experiment)
                .options(selectinload(Experiment.variants)) # noqa
                .options(selectinload(Experiment.metrics))  # noqa
                .where(Experiment.code == code)  # noqa
            )
            return list(result.scalars().all()) or None
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_paginated_with_variants(self, offset: int, limit: int) -> list[Experiment]:
        try:
            result = await self.session.execute(
                select(Experiment)
                .options(selectinload(Experiment.variants)) # noqa
                .options(selectinload(Experiment.metrics))  # noqa
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def set_status(self, id_: UUID, new_status: ExperimentStatus) -> None:
        stmt = update(Experiment).where(Experiment.id == id_).values(status=new_status) # noqa

        try:
            await self.session.execute(stmt)
            await self.session.flush()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def check_flag(
            self,
            flag_code: str
    ) -> list[Experiment] | None:
        try:
            result = await self.session.execute(
                select(Experiment)
                .options(selectinload(Experiment.variants)) # noqa
                .options(selectinload(Experiment.metrics))  # noqa
                .where(and_(
                    Experiment.flag_code == flag_code,  # noqa
                    Experiment.status.in_([ExperimentStatus.RUNNING, ExperimentStatus.PAUSED, ExperimentStatus.ROLLBACK])))  # noqa
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e
