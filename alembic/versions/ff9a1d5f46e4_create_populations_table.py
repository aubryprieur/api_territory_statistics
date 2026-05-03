"""create_populations_table

Revision ID: ff9a1d5f46e4
Revises: 04fae61fae6e
Create Date: 2025-02-26 12:34:45.049715

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# ← NE PAS MODIFIER CES LIGNES, elles sont générées par Alembic
revision: str = 'ff9a1d5f46e4'
down_revision: Union[str, None] = '04fae61fae6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_population',
        sa.Column('id',            sa.Integer(), nullable=False),
        sa.Column('iris_code',     sa.String(9),  nullable=False),
        sa.Column('com_code',      sa.String(5),  nullable=False),
        sa.Column('year',          sa.Integer(),  nullable=False),
        sa.Column('pop',           sa.Float(),    nullable=True),
        sa.Column('pop_0_2',       sa.Float(),    nullable=True),
        sa.Column('pop_3_5',       sa.Float(),    nullable=True),
        sa.Column('pop_6_10',      sa.Float(),    nullable=True),
        sa.Column('pop_11_17',     sa.Float(),    nullable=True),
        sa.Column('pop_18_24',     sa.Float(),    nullable=True),
        sa.Column('pop_25_39',     sa.Float(),    nullable=True),
        sa.Column('pop_40_54',     sa.Float(),    nullable=True),
        sa.Column('pop_55_64',     sa.Float(),    nullable=True),
        sa.Column('pop_65_79',     sa.Float(),    nullable=True),
        sa.Column('pop_80_plus',   sa.Float(),    nullable=True),
        sa.Column('pop_foreign',   sa.Float(),    nullable=True),
        sa.Column('pop_immigrant', sa.Float(),    nullable=True),
        sa.Column('pop_women',     sa.Float(),    nullable=True),
        sa.Column('pop_men',       sa.Float(),    nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iris_code', 'year', name='uq_iris_population_iris_year'),
    )
    op.create_index('ix_iris_population_iris_year', 'iris_population', ['iris_code', 'year'])
    op.create_index('ix_iris_population_com_year',  'iris_population', ['com_code',  'year'])
    op.create_index('ix_iris_population_year',      'iris_population', ['year'])


def downgrade() -> None:
    op.drop_index('ix_iris_population_year',      table_name='iris_population')
    op.drop_index('ix_iris_population_com_year',  table_name='iris_population')
    op.drop_index('ix_iris_population_iris_year', table_name='iris_population')
    op.drop_table('iris_population')
