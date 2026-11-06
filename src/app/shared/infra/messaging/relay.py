from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.domain.time import utc_now
from app.shared.infra.messaging.broker import MessageBroker
from app.shared.infra.messaging.tables import OutboxMessage, outbox_messages


class OutboxRelay:
    """Moves unsent outbox messages to the broker, oldest first.

    ``FOR UPDATE SKIP LOCKED`` lets several workers relay in parallel without sending a message twice.
    A message is marked sent only after the broker accepted it, so a crash means a resend, never a loss.
    """

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], broker: MessageBroker, batch_size: int
    ) -> None:
        self._session_factory = session_factory
        self._broker = broker
        self._batch_size = batch_size

    async def relay_once(self) -> int:
        async with self._session_factory() as session:
            stmt = (
                select(OutboxMessage)
                .where(outbox_messages.c.sent_at.is_(None))
                .order_by(outbox_messages.c.created_at, outbox_messages.c.id)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            )
            messages = list((await session.execute(stmt)).scalars())
            for message in messages:
                await self._broker.publish(message)
                message.sent_at = utc_now()
            await session.commit()
            return len(messages)
