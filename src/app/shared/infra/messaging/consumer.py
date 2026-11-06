from uuid import UUID, uuid5

from aiokafka import AIOKafkaConsumer, ConsumerRecord

from app.shared.infra.messaging.broker import MESSAGE_ID_HEADER
from app.shared.infra.messaging.dispatcher import ConsumerDispatcher

_FOREIGN_MESSAGES = UUID("6f1c3c5e-2f7a-4f0e-9d3b-0b8f6f0f4a11")


def message_id(record: ConsumerRecord[bytes, bytes]) -> UUID:
    """Our producers put the outbox id in a header; other producers' messages get an id from their position."""
    for name, value in record.headers or ():
        if name == MESSAGE_ID_HEADER:
            return UUID(value.decode())
    return uuid5(_FOREIGN_MESSAGES, f"{record.topic}:{record.partition}:{record.offset}")


class KafkaConsumerRunner:
    """Reads the topics this process has consumers for; commits an offset only after its handlers ran."""

    def __init__(self, consumer: AIOKafkaConsumer, dispatcher: ConsumerDispatcher) -> None:
        self._consumer = consumer
        self._dispatcher = dispatcher

    async def run(self) -> None:
        async for record in self._consumer:
            if record.value is not None:
                await self._dispatcher.dispatch(record.topic, message_id(record), record.value)
            await self._consumer.commit()
