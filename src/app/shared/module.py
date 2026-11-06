"""What a module hands to the composition root. ``app.bootstrap.MODULES`` lists them; nothing else does.

Adding a module is one line there: its DI provider, routes, error mapping, event subscriptions and
startup hook come along. Its tables are registered when its ``module.py`` imports them.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from dishka import AsyncContainer, Provider
from fastapi import APIRouter

from app.shared.application.events import Event, EventHandler
from app.shared.presentation.http.errors.mapping import ErrorMap


@dataclass(frozen=True, kw_only=True)
class Module:
    name: str
    provider: Callable[[], Provider]
    router: APIRouter
    errors: ErrorMap = field(default_factory=dict)
    subscriptions: Mapping[type[Event], Sequence[type[EventHandler[Any]]]] = field(default_factory=dict)
    on_startup: Callable[[AsyncContainer], Awaitable[None]] | None = None
