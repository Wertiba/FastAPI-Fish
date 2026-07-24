import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import settings
from app.core.exceptions.base import DuplicateError
from app.core.exceptions.experiment_exs import (
    ExperimentAlreadyExistsError,
    ExperimentAlreadyRunningError,
    ExperimentInvalidStatusError,
    ExperimentNotFoundError,
    ExperimentReworkError,
    VersionOfExperimentAlreadyExistsError,
)
from app.core.exceptions.flag_exs import FlagNotFoundError
from app.core.exceptions.metric_exs import MetricNotFoundError
from app.core.exceptions.user_exs import DeficiencyApproversError
from app.core.schemas.decision import DecisionBody, DecisionData, DecisionResponse
from app.core.schemas.experiment import (
    ExperimentCreateBody,
    ExperimentGuardrailsResponse,
    ExperimentHistoryResponse,
    ExperimentReadResponse,
    ExperimentResult,
    ExperimentStatus,
    ExperimentUpdate,
    ExperimentUpdateBody,
    MetricData,
    MetricRole,
    VariantData,
)
from app.core.schemas.metric import GuardrailData
from app.core.schemas.review import ReviewResult
from app.core.schemas.user import TokenData
from app.core.utils.paginated import Page, PaginationParams
from app.infrastructure.models import Decision, Experiment, Metric, Variant
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.variant_service import VariantService


class ExperimentService(VariantService):
    def __init__(self, uow: UnitOfWork):
        super().__init__(uow)

    @staticmethod
    def _convert_to_response(experiment: Experiment) -> ExperimentReadResponse:
        variants = [VariantData(**v.model_dump()) for v in experiment.variants]
        metrics = [MetricData(**m.model_dump()) for m in experiment.metrics]
        return ExperimentReadResponse(
            **experiment.model_dump(),
            variants=variants,
            metrics=metrics
        )

    @staticmethod
    async def _get_experiment_or_404(getter: Callable[[], Awaitable[Experiment | None]]) -> Experiment:
        experiment = await getter()
        if not experiment:
            raise ExperimentNotFoundError
        return experiment

    async def _generate_decisions(self, experiment_id: UUID) -> list[Decision]:
        secure_random = random.SystemRandom()
        experiment = await self.uow.experiment_repo.get_by_id_with_variants(experiment_id)
        if not experiment:
            raise ExperimentNotFoundError

        users = await self.uow.user_repo.get_all()
        if not users:
            return []

        total_users = len(users)
        participants_count = int(total_users * experiment.part / 100)

        if participants_count == 0:
            return []

        sorted_users = sorted(users, key=lambda u: u.exp_index, reverse=True)

        participating_users = []
        for user in sorted_users:
            if len(participating_users) >= participants_count:
                break

            threshold = user.exp_index / 100.0
            rand_value = secure_random.random()

            if rand_value <= threshold:
                participating_users.append(user)

        if len(participating_users) < participants_count:
            remaining = [u for u in sorted_users if u not in participating_users]
            participating_users.extend(remaining[:participants_count - len(participating_users)])

        variants = list(experiment.variants)
        variant_pool: list[Variant] = []
        for variant in variants:
            variant_pool.extend([variant] * variant.weight)

        decisions: list[Decision] = []
        secure_random.shuffle(variant_pool)

        for i, user in enumerate(participating_users):
            selected_variant = variant_pool[i % len(variant_pool)]

            existing = await self.uow.decision_repo.get_by_user_and_flag(
                user.id,
                experiment.flag_code
            )
            if not existing:
                decision = Decision(
                    user_id=user.id,
                    variant_id=selected_variant.id,
                    isRequested=False,
                )
                decisions.append(decision)
                user.exp_index *= settings.exp_index.coefficient

        for user in await self.uow.user_repo.get_all():
            if user not in participating_users and user.exp_index + settings.exp_index.term <= 100:
                user.exp_index += settings.exp_index.term

        return decisions

    async def _set_status(self, experiment: Experiment, status: ExperimentStatus) -> ExperimentReadResponse:
        await self.uow.experiment_repo.set_status(experiment.id, status)
        return ExperimentReadResponse(**experiment.model_dump(exclude={"status", "metrics"}),
                                      status=status,
                                      variants=[VariantData(**exp.model_dump()) for exp in experiment.variants],
                                      metrics=[MetricData(**exp.model_dump()) for exp in experiment.metrics])

    async def _determine_winner(self, experiment: Experiment) -> Variant | None:
        scores = await self._get_variant_scores(
            experiment,
            time_from=experiment.createdAt,
            time_to=datetime.now(tz=UTC),
            role_filter=MetricRole.MAIN,
        )
        if not scores:
            return None

        control = next((v for v in experiment.variants if v.isControl), None)
        if control and scores.get(control.id, 0) > 0:
            control_score = scores[control.id]
            scores = {
                vid: (score - control_score) / control_score
                for vid, score in scores.items()
            }

        winner_id = max(scores, key=lambda vid: scores[vid])
        return next((v for v in experiment.variants if v.id == winner_id), None)

    async def create(self, user_data: TokenData, experiment_data: ExperimentCreateBody,
                     status: ExperimentStatus | None = None) -> ExperimentReadResponse:
        async with self.uow:
            flag = await self.uow.flag_repo.get_by_code(experiment_data.flag_code)
            if not flag:
                raise FlagNotFoundError

            approvers = await self.uow.approver_repo.get_by_experimenter(user_data.id)
            if len(approvers) < user_data.required:
                raise DeficiencyApproversError

            try:
                experiment = await self.uow.experiment_repo.add(Experiment(
                    **experiment_data.model_dump(exclude={"variants", "metrics"}),
                    createdBy=user_data.id,
                    status=status,
                ))
            except DuplicateError as e:
                raise VersionOfExperimentAlreadyExistsError from e

            for variant_data in experiment_data.variants:
                await self.uow.experiment_repo.add_variant(
                    Variant(**variant_data.model_dump(), experiment_id=experiment.id))

            for metric_data in experiment_data.metrics:
                if not await self.uow.metric_repo.get_by_code(metric_data.metricCatalog_code):
                    raise MetricNotFoundError

                await self.uow.experiment_repo.add_metric(
                    Metric(**metric_data.model_dump(), experiment_id=experiment.id)
                )

            experiment = await self.uow.experiment_repo.get_by_code(experiment.code)
            return self._convert_to_response(experiment)

    async def create_new(self, user_data: TokenData, experiment_data: ExperimentCreateBody) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self.uow.experiment_repo.get_by_code(experiment_data.code)
            if experiment:
                raise ExperimentAlreadyExistsError
        return await self.create(user_data, experiment_data)

    async def get_all_experiments(self, pagination: PaginationParams) -> Page[ExperimentReadResponse]:
        async with self.uow:
            experiments = await self.uow.experiment_repo.get_paginated_with_variants(
                offset=pagination.offset,
                limit=pagination.limit
            )
            valid = [self._convert_to_response(e) for e in experiments]
            total = await self.uow.experiment_repo.count()
            return Page.build(items=valid, total=total, pagination=pagination)

    async def get_by_id(self, experiment_id: UUID) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(
                lambda: self.uow.experiment_repo.get_by_id_with_variants(experiment_id)
            )
            return self._convert_to_response(experiment)

    async def get_by_code(self, code: str, version: float | None = None) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code, version))
            return self._convert_to_response(experiment)

    async def get_history(self, code: str) -> ExperimentHistoryResponse:
        async with self.uow:
            experiments = await self.uow.experiment_repo.get_history(code)
            if not experiments:
                raise ExperimentNotFoundError
            return ExperimentHistoryResponse(versions=[self._convert_to_response(ex) for ex in experiments])

    async def get_guardrails(self, code: str) -> ExperimentGuardrailsResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code, None))
            if not experiment:
                raise ExperimentNotFoundError

            guardrails = await self.uow.metric_repo.get_guardrails_history(experiment.id)
            if not guardrails:
                raise MetricNotFoundError
            return ExperimentGuardrailsResponse(
                id=experiment.id,
                code=experiment.code,
                items=[GuardrailData(**g.model_dump()) for g in guardrails],
            )

    async def update(self, code: str, user_data: TokenData, data: ExperimentUpdateBody) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code))
            if experiment.status not in {ExperimentStatus.DRAFT, ExperimentStatus.REWORK}:
                raise ExperimentInvalidStatusError

        await self.create(
            user_data,
            ExperimentCreateBody(
                **data.model_dump(),
                code=experiment.code,
                flag_code=experiment.flag_code),
            status=ExperimentStatus.DRAFT
        )
        async with self.uow:
            await self.uow.experiment_repo.update(experiment.id, ExperimentUpdate(isCurrent=False))
            result = self._convert_to_response(await self.uow.experiment_repo.get_by_code(code))
        return result

    async def set_status(self, code: str,
                         status: ExperimentStatus, old: set[ExperimentStatus]) -> ExperimentReadResponse:
        experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code))
        if experiment.status in old:
            return await self._set_status(experiment, status)
        raise ExperimentInvalidStatusError

    async def set_status_review(self, code: str) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code))
            if experiment.status == ExperimentStatus.DRAFT:
                return await self._set_status(experiment, ExperimentStatus.IN_REVIEW)
            elif experiment.status == ExperimentStatus.REWORK:
                raise ExperimentReworkError
            raise ExperimentInvalidStatusError

    async def set_status_draft(self, code: str) -> ExperimentReadResponse:
        async with self.uow:
            return await self.set_status(code, ExperimentStatus.REWORK, {ExperimentStatus.REJECTED})

    async def stop_review(self, code: str) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code))
            if experiment.status != ExperimentStatus.IN_REVIEW:
                raise ExperimentInvalidStatusError

            results = [r.result for r in experiment.reviews]
            approved, rejected, improvement = results.count(ReviewResult.APPROVED), results.count(
                ReviewResult.REJECTED), results.count(ReviewResult.IMPROVEMENT)
            required = experiment.creator.required

            if approved >= required and approved >= rejected and approved >= improvement:
                new_status = ExperimentStatus.APPROVED
                decisions = await self._generate_decisions(experiment.id)
                for d in decisions:
                    await self.uow.decision_repo.add(d)

            elif improvement >= rejected:
                new_status = ExperimentStatus.REWORK
            else:
                new_status = ExperimentStatus.REJECTED

            return await self._set_status(experiment, new_status)

    async def set_status_running(self, code: str) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code))

            if experiment.status in {ExperimentStatus.PAUSED, ExperimentStatus.APPROVED, ExperimentStatus.ROLLBACK}:
                if experiment.status == ExperimentStatus.APPROVED:
                    active = await self.uow.experiment_repo.check_flag(experiment.flag_code)
                    if active:
                        raise ExperimentAlreadyRunningError
                return await self._set_status(experiment, ExperimentStatus.RUNNING)
            raise ExperimentInvalidStatusError

    async def set_status_paused(self, code: str) -> ExperimentReadResponse:
        async with self.uow:
            return await self.set_status(
                code,
                ExperimentStatus.PAUSED,
                {ExperimentStatus.RUNNING, ExperimentStatus.ROLLBACK}
            )

    async def get_decisions(self, data: DecisionBody) -> DecisionResponse:
        decisions: list[DecisionData] = []
        user_id = data.user_id

        async with self.uow:
            for code in data.flag_codes:
                result = await self.uow.decision_repo.get_by_user_and_flag(user_id, code)
                if not result:
                    flag = await self.uow.flag_repo.get_by_code(code)
                    if not flag:
                        raise FlagNotFoundError
                    decisions.append(DecisionData(user_id=user_id, flag_code=code, value=flag.default))
                elif result.variant.experiment.status == ExperimentStatus.ROLLBACK:
                    control_variant = next(
                        (v for v in result.variant.experiment.variants if v.isControl),
                        None
                    )

                    decisions.append(DecisionData(
                        user_id=user_id,
                        flag_code=code,
                        experiment_code=result.variant.experiment.code,
                        variant=VariantData(**control_variant.model_dump()),
                        value=control_variant.value
                    ))
                elif result.variant.experiment.status == ExperimentStatus.COMPLETED:
                    if result.variant.experiment.resultVariant_id:
                        variant = await self.uow.experiment_repo.get_by_id(result.variant.experiment.resultVariant_id)
                        decisions.append(DecisionData(
                            user_id=user_id,
                            flag_code=code,
                            experiment_code=result.variant.experiment.code,
                            variant=VariantData(**variant.model_dump()),
                            value=variant.value
                        ))
                    else:
                        flag = await self.uow.flag_repo.get_by_code(code)
                        decisions.append(DecisionData(user_id=user_id, flag_code=code, value=flag.default))
                else:
                    decisions.append(DecisionData(
                        user_id=user_id,
                        flag_code=code,
                        experiment_code=result.variant.experiment.code,
                        variant=VariantData(**result.variant.model_dump()),
                        decision_id=result.id,
                        value=result.variant.value
                    ))
        return DecisionResponse(items=decisions)

    async def set_status_completed(self, code: str, result: ExperimentResult, comment: str) -> ExperimentReadResponse:
        async with self.uow:
            experiment = await self._get_experiment_or_404(lambda: self.uow.experiment_repo.get_by_code(code))
            match result:
                case ExperimentResult.ROLLBACK:
                    control_variant = next(
                        (v for v in experiment.variants if v.isControl),
                        None
                    )
                    experiment.resultVariant_id = control_variant.id

                case ExperimentResult.ROLLOUT:
                    winner = await self._determine_winner(experiment)
                    experiment.resultVariant_id = winner.id if winner else None

                case _:
                    experiment.resultVariant_id = None

            experiment.comment = comment
            experiment.status = ExperimentStatus.COMPLETED
            return self._convert_to_response(experiment)

    async def set_status_archived(self, code: str) -> ExperimentReadResponse:
        async with self.uow:
            return await self.set_status(code, ExperimentStatus.ARCHIVED, {ExperimentStatus.COMPLETED})
