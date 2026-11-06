"""``worker`` process: relays the outbox and runs the modules' consumers (``Module.consumers``).

With ``KAFKA_BOOTSTRAP_SERVERS`` set, the outbox goes to Kafka and consumers read their topics from it,
so other services can subscribe too. Without it, the relay hands messages to this process's consumers
directly: same outbox and inbox guarantees, no broker to run. Scale replicas up to the partition count.
"""

import asyncio
import logging
from contextlib import AsyncExitStack

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dishka import AsyncContainer

from app.bootstrap import build_container, consumers
from app.shared.infra.config import KafkaConfig, WorkerConfig
from app.shared.infra.database.db_helper import DatabaseHelper
from app.shared.infra.logger import Logger
from app.shared.infra.messaging.broker import KafkaBroker, LocalBroker, MessageBroker
from app.shared.infra.messaging.consumer import KafkaConsumerRunner
from app.shared.infra.messaging.dispatcher import ConsumerDispatcher
from app.shared.infra.messaging.relay import OutboxRelay

logger = logging.getLogger(__name__)


async def relay_forever(relay: OutboxRelay, interval: float) -> None:
    while True:
        try:
            if count := await relay.relay_once():
                logger.info("outbox_relayed", extra={"count": count})
                continue  # more may be waiting
        except Exception:
            logger.exception("outbox_relay_failed")
        await asyncio.sleep(interval)


async def run_worker(container: AsyncContainer) -> None:
    kafka = await container.get(KafkaConfig)
    worker = await container.get(WorkerConfig)
    database = await container.get(DatabaseHelper)
    dispatcher = ConsumerDispatcher(container, consumers())

    async with AsyncExitStack() as stack, asyncio.TaskGroup() as group:
        broker: MessageBroker
        if kafka.bootstrap_servers:
            producer = AIOKafkaProducer(
                bootstrap_servers=kafka.bootstrap_servers, client_id=kafka.client_id, acks="all"
            )
            await producer.start()
            stack.push_async_callback(producer.stop)
            broker = KafkaBroker(producer)
            if dispatcher.topics:
                consumer = AIOKafkaConsumer(
                    *dispatcher.topics,
                    bootstrap_servers=kafka.bootstrap_servers,
                    client_id=kafka.client_id,
                    group_id=kafka.group_id,
                    enable_auto_commit=False,
                    auto_offset_reset="earliest",
                )
                await consumer.start()
                stack.push_async_callback(consumer.stop)
                group.create_task(KafkaConsumerRunner(consumer, dispatcher).run(), name="kafka-consumer")
        else:
            broker = LocalBroker(dispatcher)

        relay = OutboxRelay(database.session_factory, broker, worker.outbox_batch_size)
        group.create_task(relay_forever(relay, worker.outbox_poll_interval), name="outbox-relay")
        logger.info("process_started", extra={"process_name": "worker"})


async def main() -> None:
    container = build_container()
    await container.get(Logger)
    try:
        await run_worker(container)
    finally:
        await container.close()
        logger.info("process_stopped", extra={"process_name": "worker"})
