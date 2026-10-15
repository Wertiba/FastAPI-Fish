"""Внутрипроцессные события для связи модулей без прямых зависимостей.

Модуль-источник публикует событие (класс объявлен в его ``public.py``),
модуль-подписчик регистрирует обработчик в своём ``module.py``.
Обработчики выполняются синхронно, в той же сессии БД и транзакции,
что и команда, которая опубликовала событие.
"""

from dataclasses import dataclass
from typing import Protocol, TypeVar


@dataclass(frozen=True, kw_only=True)
class Event:
    pass


E_contra = TypeVar("E_contra", bound=Event, contravariant=True)


class EventHandler(Protocol[E_contra]):
    async def handle(self, event: E_contra) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None: ...
