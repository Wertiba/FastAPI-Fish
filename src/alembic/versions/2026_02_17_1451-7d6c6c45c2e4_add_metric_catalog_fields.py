"""add_metric_catalog_fields

Revision ID: 7d6c6c45c2e4
Revises: aea107d08746
Create Date: 2026-02-17 14:51:03.451178

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7d6c6c45c2e4'
down_revision: Union[str, Sequence[str], None] = 'aea107d08746'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    metrictype = sa.Enum('SUM', 'AVG', 'MIN', 'MAX', 'COUNT', 'RATIO', name='metrictype')
    aggregationunit = sa.Enum('USER', 'EVENT', name='aggregationunit')

    metrictype.create(op.get_bind())
    aggregationunit.create(op.get_bind())

    op.add_column('metric_catalog', sa.Column('type', metrictype, nullable=False))
    op.add_column('metric_catalog', sa.Column('aggregationUnit', aggregationunit, nullable=False))


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column('metric_catalog', 'aggregationUnit')
    op.drop_column('metric_catalog', 'type')

    sa.Enum(name='metrictype').drop(op.get_bind())
    sa.Enum(name='aggregationunit').drop(op.get_bind())
