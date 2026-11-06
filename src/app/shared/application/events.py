"""Integration events: how a module tells others that something happened without depending on them.

The publisher knows only the event; subscribers are wired in the composition root
(``Module.subscriptions``). Handlers run in the same request and the same transaction as the
publisher, so the effect is atomic. To move a module out of the process, swap the bus for an
outbox + broker: publishers and handlers stay as they are.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, kw_only=True)
class Event:
    pass


class EventHandler[E: Event](Protocol):
    async def __call__(self, event: E) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None: ...
