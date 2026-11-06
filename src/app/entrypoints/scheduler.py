"""``scheduler`` process: runs the modules' jobs (``Module.jobs``) on their schedules.

Run one replica. A second one is harmless (every run takes a distributed lock; set ``REDIS_URL`` so the
lock is shared between replicas) but useless. Jobs should be short: anything heavy belongs to the
worker -- let the job publish an integration event per unit of work instead.
"""

import logging

from app.bootstrap import build_container, jobs
from app.shared.application.ports.cache import DistributedLock
from app.shared.domain.time import TimeService
from app.shared.infra.logger import Logger
from app.shared.infra.scheduler import JobScheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    container = build_container()
    await container.get(Logger)
    scheduler = JobScheduler(container, jobs(), await container.get(DistributedLock), await container.get(TimeService))
    logger.info("process_started", extra={"process_name": "scheduler"})
    try:
        await scheduler.run()
    finally:
        await container.close()
        logger.info("process_stopped", extra={"process_name": "scheduler"})
