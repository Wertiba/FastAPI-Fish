"""Outbox and inbox: the tables that make events survive crashes and arrive once per handler."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, PrimaryKeyConstraint, String, Table, Text, Uuid

from app.shared.domain.time import utc_now
from app.shared.infra.database.registry import map_once, metadata
from app.shared.infra.database.types import UtcDateTime


@dataclass(kw_only=True)
class OutboxMessage:
    """Written in the publisher's transaction; the worker relays it and sets ``sent_at``."""

    id: UUID = field(default_factory=uuid4)
    topic: str
    key: str | None
    payload: str
    created_at: datetime = field(default_factory=utc_now)
    sent_at: datetime | None = None


@dataclass(kw_only=True)
class InboxMessage:
    """One row per (message, handler): a redelivered message is skipped, a failed one waits for replay."""

    message_id: UUID
    handler: str
    status: str
    processed_at: datetime = field(default_factory=utc_now)


INBOX_PROCESSED = "processed"
INBOX_FAILED = "failed"

outbox_messages = Table(
    "outbox_messages",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("topic", String(255), nullable=False),
    Column("key", String(255), nullable=True),
    Column("payload", Text, nullable=False),
    Column("created_at", UtcDateTime, nullable=False),
    Column("sent_at", UtcDateTime, nullable=True, index=True),
)
inbox_messages = Table(
    "inbox_messages",
    metadata,
    Column("message_id", Uuid, nullable=False),
    Column("handler", String(255), nullable=False),
    Column("status", String(20), nullable=False),
    Column("processed_at", UtcDateTime, nullable=False),
    PrimaryKeyConstraint("message_id", "handler"),
)

map_once(OutboxMessage, outbox_messages)
map_once(InboxMessage, inbox_messages)
