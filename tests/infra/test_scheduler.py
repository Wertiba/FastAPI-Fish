from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from dishka import Provider, Scope, provide

from app.bootstrap import jobs
from app.shared.application.jobs import JobSpec
from app.shared.application.ports.cache import DistributedLock
from app.shared.domain.time import TimeService
from app.shared.infra.cache import InMemoryLock
from app.shared.infra.scheduler import JobScheduler, next_run
from tests.conftest import MakeContainer

RUNS: list[str] = []


@dataclass
class Tick:
    async def __call__(self) -> None:
        RUNS.append("tick")


@dataclass
class Broken:
    async def __call__(self) -> None:
        raise RuntimeError("boom")


class JobsProvider(Provider):
    scope = Scope.REQUEST
    tick = provide(Tick)
    broken = provide(Broken)


def test_spec_needs_exactly_one_schedule() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        JobSpec(name="x", job=Tick)
    with pytest.raises(ValueError, match="exactly one"):
        JobSpec(name="x", job=Tick, every=timedelta(minutes=1), cron="* * * * *")


def test_next_run() -> None:
    at = datetime(2026, 11, 6, 18, 30, tzinfo=UTC)  # a Friday
    assert next_run(JobSpec(name="x", job=Tick, every=timedelta(minutes=5)), at) == at + timedelta(minutes=5)
    sunday_evening = next_run(JobSpec(name="x", job=Tick, cron="0 19 * * SUN"), at)
    assert sunday_evening == datetime(2026, 11, 8, 19, 0, tzinfo=UTC)


def test_modules_declare_jobs() -> None:
    assert "auth.cleanup_expired_refresh_tokens" in {spec.name for spec in jobs()}


async def test_run_job_uses_a_request_scope_and_the_lock(make_container: MakeContainer) -> None:
    container = make_container(JobsProvider())
    lock = InMemoryLock()
    scheduler = JobScheduler(container, [], lock, await container.get(TimeService))
    spec = JobSpec(name="tick", job=Tick, every=timedelta(minutes=1))

    RUNS.clear()
    await scheduler.run_job(spec)
    assert RUNS == ["tick"]

    async with lock.acquire("job:tick", timedelta(minutes=1)) as acquired:
        assert acquired
        await scheduler.run_job(spec)  # another instance holds it
    assert RUNS == ["tick"]


async def test_failing_job_does_not_stop_the_scheduler(make_container: MakeContainer) -> None:
    container = make_container(JobsProvider())
    scheduler = JobScheduler(container, [], await container.get(DistributedLock), await container.get(TimeService))
    await scheduler.run_job(JobSpec(name="broken", job=Broken, every=timedelta(minutes=1)))


async def test_auth_cleanup_job_runs(make_container: MakeContainer) -> None:
    container = make_container()
    spec = next(spec for spec in jobs() if spec.name == "auth.cleanup_expired_refresh_tokens")
    async with container() as request:
        await (await request.get(spec.job))()
