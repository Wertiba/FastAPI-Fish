"""fix_metric_role

Revision ID: 9cb212455a67
Revises: 4fdcd464b9f1
Create Date: 2026-02-19 21:54:04.728402

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9cb212455a67'
down_revision: Union[str, Sequence[str], None] = '4fdcd464b9f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    metricrole = sa.Enum('MAIN', 'ADDITIONAL', 'GUARDRAIL', name='metricrole')
    metricrole.create(op.get_bind(), checkfirst=True)

    op.alter_column('metrics', 'role',
               existing_type=sa.VARCHAR(length=255),
               type_=metricrole,
               existing_nullable=False,
               postgresql_using='role::metricrole')
    op.drop_constraint(op.f('metrics_addedBy_fkey'), 'metrics', type_='foreignkey')
    op.drop_column('metrics', 'createdAt')
    op.drop_column('metrics', 'addedBy')


def downgrade() -> None:
    op.add_column('metrics', sa.Column('addedBy', sa.UUID(), autoincrement=False, nullable=False))
    op.add_column('metrics', sa.Column('createdAt', postgresql.TIMESTAMP(), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('metrics_addedBy_fkey'), 'metrics', 'users', ['addedBy'], ['id'])
    op.alter_column('metrics', 'role',
               existing_type=sa.Enum('MAIN', 'ADDITIONAL', 'GUARDRAIL', name='metricrole'),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False,
               postgresql_using='role::varchar')

    metricrole = sa.Enum('MAIN', 'ADDITIONAL', 'GUARDRAIL', name='metricrole')
    metricrole.drop(op.get_bind(), checkfirst=True)
