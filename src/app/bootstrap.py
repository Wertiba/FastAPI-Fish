"""Composition root: the list of modules and the DI container every process builds from them.

Importing this module imports every module, which registers its tables on the shared metadata.
The processes in ``app.entrypoints`` take from here what they serve.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from dishka import AsyncContainer, Provider, make_async_container

from app.modules.auth.module import auth_module
from app.modules.users.module import users_module
from app.shared.application.events import Event, EventHandler, IntegrationEvent
from app.shared.application.jobs import JobSpec
from app.shared.infra.cache import CacheProvider
from app.shared.infra.database.di import DatabaseProvider
from app.shared.infra.di import ConfigProvider
from app.shared.infra.llm import LlmProvider
from app.shared.infra.messaging.bus import EventBusProvider
from app.shared.infra.push import PushProvider
from app.shared.infra.storage import StorageProvider
from app.shared.infra.telegram import TelegramProvider
from app.shared.module import Module
from app.shared.presentation.http.errors.mapping import SHARED_ERRORS, ErrorFactory

MODULES: tuple[Module, ...] = (
    auth_module,
    users_module,
)


def _merge[K, V](parts: Sequence[Mapping[K, Sequence[V]]]) -> dict[K, list[V]]:
    merged: dict[K, list[V]] = {}
    for part in parts:
        for key, values in part.items():
            merged.setdefault(key, []).extend(values)
    return merged


def subscriptions(modules: Sequence[Module] = MODULES) -> Mapping[type[Event], Sequence[type[EventHandler[Any]]]]:
    return _merge([module.subscriptions for module in modules])


def consumers(
    modules: Sequence[Module] = MODULES,
) -> Mapping[type[IntegrationEvent], Sequence[type[EventHandler[Any]]]]:
    return _merge([module.consumers for module in modules])


def jobs(modules: Sequence[Module] = MODULES) -> list[JobSpec]:
    specs = [spec for module in modules for spec in module.jobs]
    names = [spec.name for spec in specs]
    if duplicates := {name for name in names if names.count(name) > 1}:
        raise ValueError(f"Duplicate job names: {sorted(duplicates)}")
    return specs


def error_map(modules: Sequence[Module] = MODULES) -> dict[type[Exception], ErrorFactory]:
    """Module errors first: they subclass the shared ones, and the first match wins."""
    merged: dict[type[Exception], ErrorFactory] = {}
    for module in modules:
        merged.update(module.errors)
    merged.update(SHARED_ERRORS)
    return merged


def build_container(*providers: Provider) -> AsyncContainer:
    """Extra ``providers`` go last: an entrypoint adds its framework integration, tests override with ``override=True``.

    External systems are created lazily, on first use: the API never connects to Kafka, the bot never to S3.
    """
    return make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        CacheProvider(),
        StorageProvider(),
        LlmProvider(),
        TelegramProvider(),
        PushProvider(),
        EventBusProvider(subscriptions()),
        *(module.provider() for module in MODULES),
        *providers,
    )
