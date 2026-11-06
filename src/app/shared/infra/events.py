from collections.abc import Mapping, Sequence
from typing import Any

from dishka import AsyncContainer, Provider, Scope, provide

from app.shared.application.events import Event, EventHandler, EventPublisher

type Subscriptions = Mapping[type[Event], Sequence[type[EventHandler[Any]]]]


class InProcessEventBus(EventPublisher):
    """Resolves each subscriber from the request container, so it shares the request's unit of work."""

    def __init__(self, container: AsyncContainer, subscriptions: Subscriptions) -> None:
        self._container = container
        self._subscriptions = subscriptions

    async def publish(self, event: Event) -> None:
        for handler_type in self._subscriptions.get(type(event), ()):
            handler = await self._container.get(handler_type)
            await handler(event)


class EventBusProvider(Provider):
    def __init__(self, subscriptions: Subscriptions) -> None:
        super().__init__()
        self._subscriptions = subscriptions

    @provide(scope=Scope.REQUEST)
    def bus(self, container: AsyncContainer) -> EventPublisher:
        return InProcessEventBus(container, self._subscriptions)
