import asyncio
import logging
import time
from collections.abc import Sequence
from datetime import datetime, timedelta

from croniter import croniter
from dishka import AsyncContainer

from app.shared.application.jobs import JobSpec
from app.shared.application.ports.cache import DistributedLock
from app.shared.domain.time import TimeService

logger = logging.getLogger(__name__)


def next_run(spec: JobSpec, after: datetime) -> datetime:
    if spec.every is not None:
        return after + spec.every
    if spec.cron is None:
        raise ValueError(f"Job {spec.name!r} has no schedule")
    return croniter(spec.cron, after).get_next(datetime)


class JobScheduler:
    """Runs every job on its schedule, each run under a distributed lock and in its own DI request scope.

    The lock lets a spare scheduler replica (or a second one by mistake) run without double runs.
    It is held for ``lock_ttl``, which should exceed the job's duration.
    """

    def __init__(
        self,
        container: AsyncContainer,
        specs: Sequence[JobSpec],
        lock: DistributedLock,
        time: TimeService,
        lock_ttl: timedelta = timedelta(minutes=5),
    ) -> None:
        self._container = container
        self._specs = specs
        self._lock = lock
        self._time = time
        self._lock_ttl = lock_ttl

    async def run_job(self, spec: JobSpec) -> None:
        """One run, now. Errors are logged, not raised: the next tick tries again."""
        async with self._lock.acquire(f"job:{spec.name}", self._lock_ttl) as acquired:
            if not acquired:
                logger.info("job_skipped", extra={"job": spec.name})
                return
            started = time.perf_counter()
            try:
                async with self._container() as request:
                    job = await request.get(spec.job)
                    await job()
            except Exception:
                logger.exception("job_failed", extra={"job": spec.name})
                return
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            logger.info("job_completed", extra={"job": spec.name, "duration_ms": duration_ms})

    async def _loop(self, spec: JobSpec) -> None:
        due = next_run(spec, self._time.now())
        while True:
            await asyncio.sleep(max((due - self._time.now()).total_seconds(), 0))
            await self.run_job(spec)
            # Skip the ticks missed while the job ran instead of running them back to back.
            due = next_run(spec, max(due, self._time.now()))

    async def run(self) -> None:
        async with asyncio.TaskGroup() as group:
            for spec in self._specs:
                group.create_task(self._loop(spec), name=f"job:{spec.name}")
