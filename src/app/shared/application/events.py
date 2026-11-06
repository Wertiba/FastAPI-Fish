"""Events: how a module tells others that something happened without depending on them.

Two kinds of subscription, both wired in the composition root (``Module``):

* ``Module.subscriptions`` -- handlers run in the publisher's request and transaction, so the
  effect is atomic ("user deactivated -> revoke sessions").
* ``Module.consumers`` -- for an ``IntegrationEvent`` only: handlers run later in the ``worker``
  process, each in its own transaction, at least once ("event scheduled -> plan reminders").

Publishing an ``IntegrationEvent`` also writes it to the outbox in the same transaction; the worker
relays the outbox to Kafka (or straight to local consumers when Kafka is not configured).
Handlers look the same in both cases, so moving a reaction from sync to async is one line.
"""

from dataclasses import dataclass
from typing import ClassVar, Protocol


@dataclass(frozen=True, kw_only=True)
class Event:
    pass


@dataclass(frozen=True, kw_only=True)
class IntegrationEvent(Event):
    """An event that leaves the transaction: goes through the outbox to the broker.

    ``topic`` is ``<module>.<entity>.<fact in past tense>``; ``key`` keeps the events of one aggregate
    in order. The payload is the dataclass fields; change it compatibly only (new fields optional).
    """

    topic: ClassVar[str]

    def key(self) -> str | None:
        return None


class EventHandler[E: Event](Protocol):
    async def __call__(self, event: E) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None: ...
