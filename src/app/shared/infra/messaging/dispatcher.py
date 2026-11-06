import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.application.events import EventHandler, IntegrationEvent
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.infra.messaging.serialization import from_payload
from app.shared.infra.messaging.tables import INBOX_FAILED, INBOX_PROCESSED, InboxMessage

logger = logging.getLogger(__name__)

type Consumers = Mapping[type[IntegrationEvent], Sequence[type[EventHandler[Any]]]]


def handler_name(handler_type: type) -> str:
    return f"{handler_type.__module__}.{handler_type.__qualname__}"


class ConsumerDispatcher:
    """Delivers one broker message to every local consumer of its topic, each in its own transaction.

    Delivery is at least once, so the inbox makes it once per handler: a processed (or dead) message is
    skipped. A handler that keeps failing is recorded as ``failed`` after ``max_attempts`` and the
    stream moves on; delete that inbox row and resend the message to replay it.
    """

    def __init__(
        self,
        container: AsyncContainer,
        consumers: Consumers,
        max_attempts: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        self._container = container
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay
        self._routes: dict[str, tuple[type[IntegrationEvent], Sequence[type[EventHandler[Any]]]]] = {
            event_cls.topic: (event_cls, handlers) for event_cls, handlers in consumers.items()
        }

    @property
    def topics(self) -> list[str]:
        return sorted(self._routes)

    async def dispatch(self, topic: str, message_id: UUID, payload: str | bytes) -> None:
        route = self._routes.get(topic)
        if route is None:
            return
        event_cls, handlers = route
        event = from_payload(event_cls, payload)
        for handler_type in handlers:
            await self._deliver(handler_type, topic, message_id, event)

    async def _deliver(
        self, handler_type: type[EventHandler[Any]], topic: str, message_id: UUID, event: IntegrationEvent
    ) -> None:
        name = handler_name(handler_type)
        for attempt in range(1, self._max_attempts + 1):
            try:
                async with self._container() as request:
                    session = await request.get(AsyncSession)
                    if await session.get(InboxMessage, (message_id, name)) is not None:
                        return
                    handler = await request.get(handler_type)
                    await handler(event)
                    uow = await request.get(UnitOfWork)
                    await uow.add(InboxMessage(message_id=message_id, handler=name, status=INBOX_PROCESSED))
                    await uow.commit()
                    return
            except Exception:
                logger.warning("message_failed", extra={"topic": topic, "handler": name}, exc_info=True)
                if attempt < self._max_attempts:
                    await asyncio.sleep(self._retry_delay * 2 ** (attempt - 1))
        async with self._container() as request:
            uow = await request.get(UnitOfWork)
            await uow.add(InboxMessage(message_id=message_id, handler=name, status=INBOX_FAILED))
            await uow.commit()
        logger.error("message_dead_lettered", extra={"topic": topic, "handler": name})
