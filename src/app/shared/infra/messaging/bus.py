from collections.abc import Mapping, Sequence
from typing import Any

from dishka import AsyncContainer, Provider, Scope, provide

from app.shared.application.events import Event, EventHandler, EventPublisher, IntegrationEvent
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.infra.messaging.serialization import to_payload
from app.shared.infra.messaging.tables import OutboxMessage

type Subscriptions = Mapping[type[Event], Sequence[type[EventHandler[Any]]]]


class InProcessEventBus(EventPublisher):
    """Runs in-process subscribers in the request's transaction; an ``IntegrationEvent`` also goes to the outbox.

    Subscribers are resolved from the request container, so they share the request's unit of work.
    """

    def __init__(self, container: AsyncContainer, subscriptions: Subscriptions, uow: UnitOfWork) -> None:
        self._container = container
        self._subscriptions = subscriptions
        self._uow = uow

    async def publish(self, event: Event) -> None:
        for handler_type in self._subscriptions.get(type(event), ()):
            handler = await self._container.get(handler_type)
            await handler(event)
        if isinstance(event, IntegrationEvent):
            await self._uow.add(OutboxMessage(topic=event.topic, key=event.key(), payload=to_payload(event)))


class EventBusProvider(Provider):
    def __init__(self, subscriptions: Subscriptions) -> None:
        super().__init__()
        self._subscriptions = subscriptions

    @provide(scope=Scope.REQUEST)
    def bus(self, container: AsyncContainer, uow: UnitOfWork) -> EventPublisher:
        return InProcessEventBus(container, self._subscriptions, uow)
