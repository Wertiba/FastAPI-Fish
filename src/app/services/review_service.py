from uuid import UUID

from app.core.exceptions.base import DuplicateError
from app.core.exceptions.experiment_exs import ExperimentInvalidStatusError, ExperimentNotFoundError
from app.core.exceptions.review_exs import ReviewAlreadyExistsError, ReviewNotFoundError
from app.core.exceptions.user_exs import ForbiddenError
from app.core.schemas.experiment import ExperimentStatus
from app.core.schemas.review import ReviewCreateBody, ReviewReadResponse, ReviewResultsResponse
from app.core.schemas.user import TokenData
from app.infrastructure.models import Experiment, Review
from app.infrastructure.unit_of_work import UnitOfWork


class ReviewService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def _get_experiment_by_code(self, code: str, version: float | None = None) -> Experiment | None:
        experiment = await self.uow.experiment_repo.get_by_code(code, version)
        if experiment is None:
            raise ExperimentNotFoundError
        return experiment

    async def create(self, user_data: TokenData, review_data: ReviewCreateBody) -> ReviewReadResponse:
        async with self.uow:
            try:
                experiment = await self._get_experiment_by_code(review_data.experiment_code)
                if experiment.status != ExperimentStatus.IN_REVIEW:
                    raise ExperimentInvalidStatusError
                approver = await self.uow.approver_repo.get_by_two_ids(experiment.createdBy, user_data.id)
                if not approver:
                    raise ForbiddenError

                review = await self.uow.review_repo.add(Review(
                    **review_data.model_dump(exclude={"experiment_code"}),
                    approvedBy=approver.id,
                    experiment_id=experiment.id
                ))
                return ReviewReadResponse(**review.model_dump(), experiment_code=review_data.experiment_code)
            except DuplicateError:
                raise ReviewAlreadyExistsError from DuplicateError

    async def get_by_id(self, review_id: UUID) -> ReviewReadResponse | None:
        async with self.uow:
            review_exists = await self.uow.review_repo.get_by_id(review_id)
            if not review_exists:
                raise ReviewNotFoundError
            experiment = await self.uow.experiment_repo.get_by_id(review_exists.experiment_id)

            return ReviewReadResponse(**review_exists.model_dump(), experiment_code=experiment.code)

    async def get_all(self, exp_code: str, version: float | None = None) -> ReviewResultsResponse:
        async with self.uow:
            experiment = await self._get_experiment_by_code(exp_code, version)
            reviews = await self.uow.review_repo.get_by_experiment(experiment.id)
            valid = [ReviewReadResponse(**r.model_dump(), experiment_code=exp_code) for r in reviews]
            return ReviewResultsResponse(required=experiment.creator.required, items=valid)
