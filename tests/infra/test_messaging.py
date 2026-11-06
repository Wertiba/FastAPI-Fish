"""Outbox -> relay -> consumers, on the test database, with the local broker (no Kafka)."""

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID, uuid4

from dishka import AsyncContainer, Provider, Scope, provide
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.application.events import EventPublisher, IntegrationEvent
from app.shared.application.ports.unit_of_work import UnitOfWork
from app.shared.infra.database.db_helper import DatabaseHelper
from app.shared.infra.messaging.broker import LocalBroker
from app.shared.infra.messaging.dispatcher import ConsumerDispatcher, handler_name
from app.shared.infra.messaging.relay import OutboxRelay
from app.shared.infra.messaging.serialization import from_payload, to_payload
from app.shared.infra.messaging.tables import INBOX_FAILED, INBOX_PROCESSED, InboxMessage, OutboxMessage
from tests.conftest import MakeContainer, RegisterUser


@dataclass(frozen=True, kw_only=True)
class ThingHappened(IntegrationEvent):
    topic: ClassVar[str] = "tests.thing.happened"

    thing_id: UUID
    name: str

    def key(self) -> str:
        return str(self.thing_id)


SEEN: list[UUID] = []


@dataclass
class RememberThing:
    async def __call__(self, event: ThingHappened) -> None:
        SEEN.append(event.thing_id)


@dataclass
class AlwaysFails:
    async def __call__(self, event: ThingHappened) -> None:
        raise RuntimeError("boom")


class HandlersProvider(Provider):
    scope = Scope.REQUEST
    remember = provide(RememberThing)
    fails = provide(AlwaysFails)


async def publish(container: AsyncContainer, event: IntegrationEvent) -> None:
    async with container() as request:
        await (await request.get(EventPublisher)).publish(event)
        await (await request.get(UnitOfWork)).commit()


async def relay(container: AsyncContainer, dispatcher: ConsumerDispatcher) -> int:
    database = await container.get(DatabaseHelper)
    return await OutboxRelay(database.session_factory, LocalBroker(dispatcher), batch_size=10).relay_once()


def test_payload_round_trip() -> None:
    event = ThingHappened(thing_id=uuid4(), name="Барсик")
    assert from_payload(ThingHappened, to_payload(event)) == event


async def test_event_goes_through_outbox_to_consumer_once(
    make_container: MakeContainer, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    container = make_container(HandlersProvider())
    dispatcher = ConsumerDispatcher(container, {ThingHappened: [RememberThing]}, retry_delay=0)
    event = ThingHappened(thing_id=uuid4(), name="x")

    await publish(container, event)
    async with db_session_factory() as session:
        stored = (await session.execute(select(OutboxMessage))).scalar_one()
    assert stored.topic == "tests.thing.happened"
    assert stored.key == str(event.thing_id)
    assert stored.sent_at is None

    assert await relay(container, dispatcher) == 1
    assert event.thing_id in SEEN
    assert await relay(container, dispatcher) == 0  # marked sent

    # At-least-once: the broker redelivers; the inbox keeps the handler from running twice.
    before = SEEN.count(event.thing_id)
    await dispatcher.dispatch(stored.topic, stored.id, stored.payload)
    assert SEEN.count(event.thing_id) == before
    async with db_session_factory() as session:
        inbox = await session.get(InboxMessage, (stored.id, handler_name(RememberThing)))
    assert inbox is not None
    assert inbox.status == INBOX_PROCESSED


async def test_failing_consumer_is_recorded_and_does_not_block(
    make_container: MakeContainer, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    container = make_container(HandlersProvider())
    dispatcher = ConsumerDispatcher(container, {ThingHappened: [AlwaysFails, RememberThing]}, retry_delay=0)
    event = ThingHappened(thing_id=uuid4(), name="x")
    message_id = uuid4()

    await dispatcher.dispatch(ThingHappened.topic, message_id, to_payload(event))

    assert event.thing_id in SEEN  # the next handler still ran
    async with db_session_factory() as session:
        failed = await session.get(InboxMessage, (message_id, handler_name(AlwaysFails)))
    assert failed is not None
    assert failed.status == INBOX_FAILED


async def test_unknown_topic_is_ignored(make_container: MakeContainer) -> None:
    dispatcher = ConsumerDispatcher(make_container(), {})
    await dispatcher.dispatch("nobody.listens", uuid4(), b"{}")


def test_user_deactivation_is_written_to_the_outbox(
    client: TestClient,
    register_user: RegisterUser,
    admin_headers: dict[str, str],
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = register_user()
    assert client.delete(f"/api/v1/users/{user['user']['id']}", headers=admin_headers).status_code == 204

    async def outbox() -> list[OutboxMessage]:
        async with db_session_factory() as session:
            return list((await session.execute(select(OutboxMessage))).scalars())

    messages = client.portal.call(outbox)  # type: ignore[union-attr]
    assert [(m.topic, m.key) for m in messages] == [("users.user.deactivated", user["user"]["id"])]
