"""Scheduled jobs: a module declares what runs when; the ``scheduler`` process runs it.

A job is a use case with no arguments. It works from the state of the database ("everything due
and not sent yet"), not from the time of the tick, so a missed or repeated tick loses and
duplicates nothing.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol


class Job(Protocol):
    async def __call__(self) -> None: ...


@dataclass(frozen=True, kw_only=True)
class JobSpec:
    """Exactly one of ``every`` and ``cron`` (5 fields, UTC: ``"0 19 * * SUN"``)."""

    name: str
    job: type[Job]
    every: timedelta | None = None
    cron: str | None = None

    def __post_init__(self) -> None:
        if (self.every is None) == (self.cron is None):
            raise ValueError(f"Job {self.name!r}: set exactly one of 'every' and 'cron'")
