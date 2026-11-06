from typing import Protocol

from aiokafka import AIOKafkaProducer

from app.shared.infra.messaging.dispatcher import ConsumerDispatcher
from app.shared.infra.messaging.tables import OutboxMessage

MESSAGE_ID_HEADER = "message_id"


class MessageBroker(Protocol):
    async def publish(self, message: OutboxMessage) -> None:
        """Returns once the broker has the message; raises if it has not."""
        ...


class KafkaBroker(MessageBroker):
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def publish(self, message: OutboxMessage) -> None:
        await self._producer.send_and_wait(
            message.topic,
            value=message.payload.encode(),
            key=message.key.encode() if message.key else None,
            headers=[(MESSAGE_ID_HEADER, str(message.id).encode())],
        )


class LocalBroker(MessageBroker):
    """No Kafka: the worker hands outbox messages straight to this process's consumers.

    Same guarantees inside the monolith (outbox + inbox), no external subscribers. Setting
    ``KAFKA_BOOTSTRAP_SERVERS`` switches to Kafka without touching publishers or handlers.
    """

    def __init__(self, dispatcher: ConsumerDispatcher) -> None:
        self._dispatcher = dispatcher

    async def publish(self, message: OutboxMessage) -> None:
        await self._dispatcher.dispatch(message.topic, message.id, message.payload)
