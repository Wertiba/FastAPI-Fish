"""fix_guardrail_actions

Revision ID: ed12444aa6d1
Revises: aa7318a64fbf
Create Date: 2026-02-19 23:13:25.393903

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ed12444aa6d1'
down_revision: Union[str, Sequence[str], None] = 'aa7318a64fbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    guardrailaction = sa.Enum('PAUSE', 'ROLLBACK', name='guardrailaction')
    guardrailaction.create(op.get_bind(), checkfirst=True)

    op.add_column('metrics', sa.Column('action_code', guardrailaction, nullable=True))


def downgrade() -> None:
    op.drop_column('metrics', 'action_code')

    guardrailaction = sa.Enum('PAUSE', 'ROLLBACK', name='guardrailaction')
    guardrailaction.drop(op.get_bind(), checkfirst=True)
