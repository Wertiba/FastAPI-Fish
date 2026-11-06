"""outbox and inbox for integration events

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_messages")),
    )
    op.create_index(op.f("ix_outbox_messages_sent_at"), "outbox_messages", ["sent_at"], unique=False)
    op.create_table(
        "inbox_messages",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("handler", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("message_id", "handler", name=op.f("pk_inbox_messages")),
    )


def downgrade() -> None:
    op.drop_table("inbox_messages")
    op.drop_index(op.f("ix_outbox_messages_sent_at"), table_name="outbox_messages")
    op.drop_table("outbox_messages")
