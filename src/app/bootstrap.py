"""Composition root: the list of modules and the DI container built from them.

Importing this module imports every module, which registers its tables on the shared metadata.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from dishka import AsyncContainer, Provider, make_async_container

from app.modules.auth.module import auth_module
from app.modules.users.module import users_module
from app.shared.application.events import Event, EventHandler
from app.shared.infra.database.di import DatabaseProvider
from app.shared.infra.di import ConfigProvider
from app.shared.infra.events import EventBusProvider
from app.shared.module import Module
from app.shared.presentation.http.errors.mapping import SHARED_ERRORS, ErrorFactory

MODULES: tuple[Module, ...] = (
    auth_module,
    users_module,
)


def subscriptions(modules: Sequence[Module] = MODULES) -> Mapping[type[Event], Sequence[type[EventHandler[Any]]]]:
    merged: dict[type[Event], list[type[EventHandler[Any]]]] = {}
    for module in modules:
        for event, handlers in module.subscriptions.items():
            merged.setdefault(event, []).extend(handlers)
    return merged


def error_map(modules: Sequence[Module] = MODULES) -> dict[type[Exception], ErrorFactory]:
    """Module errors first: they subclass the shared ones, and the first match wins."""
    merged: dict[type[Exception], ErrorFactory] = {}
    for module in modules:
        merged.update(module.errors)
    merged.update(SHARED_ERRORS)
    return merged


def build_container(*providers: Provider) -> AsyncContainer:
    """Extra ``providers`` go last, so tests can override any dependency with ``override=True``."""
    return make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        EventBusProvider(subscriptions()),
        *(module.provider() for module in MODULES),
        *providers,
    )
