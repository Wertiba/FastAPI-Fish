"""Описание модуля для composition root.

Каждый модуль экспортирует один объект ``Module`` из своего ``module.py``,
а ``app/modules/__init__.py`` перечисляет их в ``MODULES``. Больше ничего
в bootstrap при добавлении нового домена трогать не нужно.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from dishka import Provider
from fastapi import APIRouter

from app.shared.application.events import Event, EventHandler


@dataclass(frozen=True, kw_only=True)
class Module:
    name: str
    providers: Sequence[Provider] = ()
    routers: Sequence[APIRouter] = ()
    map_tables: Callable[[], None] | None = None
    subscriptions: Mapping[type[Event], Sequence[type[EventHandler[Any]]]] = field(default_factory=dict)
