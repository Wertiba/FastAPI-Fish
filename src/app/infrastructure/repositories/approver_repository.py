from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.exceptions.base import RepositoryError
from app.infrastructure.models import Approver
from app.infrastructure.repositories.base_repo import BaseRepository


class ApproverRepository(BaseRepository[Approver]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=Approver)

    async def get_by_experimenter(self, expr_id: UUID) -> list[Approver]:
        try:
            stmt = select(Approver).where(
                Approver.experimenter_id == expr_id,    # noqa
                Approver.isActive.is_(True) # noqa
            )
            res = await self.session.execute(stmt)
            return list(res.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_two_ids(self, expr_id: UUID, appr_id: UUID) -> Approver | None:
        try:
            stmt = select(Approver).where(
                and_(
                    Approver.experimenter_id == expr_id,  # noqa
                    Approver.approver_id == appr_id,  # noqa
                    Approver.isActive.is_(True)  # noqa
                )
            )
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e
