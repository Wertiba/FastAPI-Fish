"""fix_experiments_variants_fk

Revision ID: 004fd90411c8
Revises: 73df3b7ab643
Create Date: 2026-02-17 23:51:04.673619

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '004fd90411c8'
down_revision: Union[str, Sequence[str], None] = '73df3b7ab643'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('variants', sa.Column('experiment_id', sa.Uuid(), nullable=True))

    op.execute("""
        UPDATE variants
        SET experiment_id = experiments.id
        FROM experiments
        WHERE variants.experiment_code = experiments.code
    """)

    op.alter_column('variants', 'experiment_id', nullable=False)

    op.drop_constraint('variants_experiment_code_fkey', 'variants', type_='foreignkey')

    op.create_foreign_key(
        'variants_experiment_id_fkey',
        'variants',
        'experiments',
        ['experiment_id'],
        ['id']
    )

    op.drop_column('variants', 'experiment_code')
    op.drop_column('variants', 'updatedAt')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('variants', sa.Column('experiment_code', sa.VARCHAR(), nullable=True))
    op.add_column('variants', sa.Column('updatedAt', postgresql.TIMESTAMP(timezone=True), nullable=True))

    op.execute("""
        UPDATE variants
        SET experiment_code = experiments.code,
            "updatedAt" = NOW()
        FROM experiments
        WHERE variants.experiment_id = experiments.id
    """)

    op.alter_column('variants', 'experiment_code', nullable=False)
    op.alter_column('variants', 'updatedAt', nullable=False)

    op.drop_constraint('variants_experiment_id_fkey', 'variants', type_='foreignkey')

    op.create_foreign_key(
        'variants_experiment_code_fkey',
        'variants',
        'experiments',
        ['experiment_code'],
        ['code']
    )

    op.drop_column('variants', 'experiment_id')
