from collections import defaultdict
from typing import Any

from dishka import AsyncContainer
from loguru import logger

from app.shared.application.events import Event, EventHandler, EventPublisher


class EventRegistry:
    """Кто на какое событие подписан. Заполняется из ``Module.subscriptions`` при старте."""

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[type[EventHandler[Any]]]] = defaultdict(list)

    def subscribe(self, event_type: type[Event], handler_type: type[EventHandler[Any]]) -> None:
        if handler_type not in self._handlers[event_type]:
            self._handlers[event_type].append(handler_type)

    def handlers_for(self, event_type: type[Event]) -> list[type[EventHandler[Any]]]:
        return list(self._handlers.get(event_type, ()))


class InProcessEventBus(EventPublisher):
    """Достаёт обработчики из request-контейнера Dishka: та же сессия, та же транзакция."""

    def __init__(self, container: AsyncContainer, registry: EventRegistry) -> None:
        self._container = container
        self._registry = registry

    async def publish(self, event: Event) -> None:
        for handler_type in self._registry.handlers_for(type(event)):
            handler = await self._container.get(handler_type)
            logger.debug("event {} -> {}", type(event).__name__, handler_type.__name__)
            await handler.handle(event)
