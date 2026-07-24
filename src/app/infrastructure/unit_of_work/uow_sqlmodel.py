from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import (
    ApproverRepository,
    DecisionRepository,
    EventRepository,
    ExperimentRepository,
    FlagRepository,
    MetricRepository,
    ReviewRepository,
    RoleRepository,
    UserRepository,
)
from app.infrastructure.unit_of_work import AbstractUnitOfWork


class UnitOfWork(AbstractUnitOfWork):
    user_repo: UserRepository
    flag_repo: FlagRepository
    role_repo: RoleRepository
    metric_repo: MetricRepository
    experiment_repo: ExperimentRepository
    decision_repo: DecisionRepository
    approver_repo: ApproverRepository
    review_repo: ReviewRepository
    event_repo: EventRepository

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        self.user_repo = UserRepository(self.session)
        self.flag_repo = FlagRepository(self.session)
        self.role_repo = RoleRepository(self.session)
        self.metric_repo = MetricRepository(self.session)
        self.experiment_repo = ExperimentRepository(self.session)
        self.decision_repo = DecisionRepository(self.session)
        self.approver_repo = ApproverRepository(self.session)
        self.review_repo = ReviewRepository(self.session)
        self.event_repo = EventRepository(self.session)
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
