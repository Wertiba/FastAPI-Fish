"""fix_unicue_code_experiments

Revision ID: 8a60a15920e6
Revises: 004fd90411c8
Create Date: 2026-02-18 10:46:59.933952

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8a60a15920e6'
down_revision: Union[str, Sequence[str], None] = '004fd90411c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('reviews', sa.Column('experiment_id', sa.Uuid(), nullable=True))

    op.execute("""
        UPDATE reviews
        SET experiment_id = experiments.id
        FROM experiments
        WHERE reviews.experiment_code = experiments.code
    """)

    op.alter_column('reviews', 'experiment_id', nullable=False)

    op.drop_constraint('reviews_experiment_code_fkey', 'reviews', type_='foreignkey')

    op.drop_index('ix_experiments_code', table_name='experiments')
    op.create_index('ix_experiments_code', 'experiments', ['code'], unique=False)

    op.create_foreign_key(
        'reviews_experiment_id_fkey',
        'reviews',
        'experiments',
        ['experiment_id'],
        ['id']
    )

    op.drop_column('reviews', 'experiment_code')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('reviews', sa.Column('experiment_code', sa.VARCHAR(), nullable=True))

    op.execute("""
        UPDATE reviews
        SET experiment_code = experiments.code
        FROM experiments
        WHERE reviews.experiment_id = experiments.id
    """)

    op.alter_column('reviews', 'experiment_code', nullable=False)

    op.drop_constraint('reviews_experiment_id_fkey', 'reviews', type_='foreignkey')

    op.drop_index('ix_experiments_code', table_name='experiments')
    op.create_index('ix_experiments_code', 'experiments', ['code'], unique=True)

    op.create_foreign_key(
        'reviews_experiment_code_fkey',
        'reviews',
        'experiments',
        ['experiment_code'],
        ['code']
    )

    op.drop_column('reviews', 'experiment_id')
