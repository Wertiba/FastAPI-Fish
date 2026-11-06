"""What a module hands to the composition root. ``app.bootstrap.MODULES`` lists them; nothing else does.

Adding a module is one line there. Everything it plugs into comes along, and each process takes
only its part:

* ``api``       -- ``router``, ``errors``, ``on_startup``
* ``bot``       -- ``bot_router``
* ``worker``    -- ``consumers``
* ``scheduler`` -- ``jobs``
* every process -- ``provider`` and ``subscriptions`` (the same DI graph everywhere)

Its tables are registered when its ``module.py`` imports them.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from aiogram import Router as BotRouter
from dishka import AsyncContainer, Provider
from fastapi import APIRouter

from app.shared.application.events import Event, EventHandler, IntegrationEvent
from app.shared.application.jobs import JobSpec
from app.shared.presentation.http.errors.mapping import ErrorMap


@dataclass(frozen=True, kw_only=True)
class Module:
    name: str
    provider: Callable[[], Provider]
    router: APIRouter | None = None
    errors: ErrorMap = field(default_factory=dict)
    # Same transaction as the publisher, any process.
    subscriptions: Mapping[type[Event], Sequence[type[EventHandler[Any]]]] = field(default_factory=dict)
    # Later, in the worker, through the outbox and the broker.
    consumers: Mapping[type[IntegrationEvent], Sequence[type[EventHandler[Any]]]] = field(default_factory=dict)
    jobs: Sequence[JobSpec] = ()
    bot_router: BotRouter | None = None
    on_startup: Callable[[AsyncContainer], Awaitable[None]] | None = None
