"""create_iris_families_table

Revision ID: 6bf7bc21ddf0
Revises: 9f583757ca4e
Create Date: 2026-05-03 15:08:48.169058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bf7bc21ddf0'
down_revision: Union[str, None] = '9f583757ca4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_families',
        sa.Column('id',                sa.Integer(),     nullable=False),
        sa.Column('iris_code',         sa.String(9),     nullable=False),
        sa.Column('com_code',          sa.String(5),     nullable=False),
        sa.Column('iris_name',         sa.String(255),   nullable=True),
        sa.Column('dep_code',          sa.String(3),     nullable=True),
        sa.Column('reg_code',          sa.String(2),     nullable=True),
        sa.Column('year',              sa.Integer(),     nullable=False),
        # Population 15 ans ou plus
        sa.Column('pop_15p',           sa.Float(),       nullable=True),
        sa.Column('pop_15_24',         sa.Float(),       nullable=True),
        sa.Column('pop_25_54',         sa.Float(),       nullable=True),
        sa.Column('pop_55_79',         sa.Float(),       nullable=True),
        sa.Column('pop_80p',           sa.Float(),       nullable=True),
        # Personnes vivant seules
        sa.Column('pop_15p_alone',     sa.Float(),       nullable=True),
        sa.Column('pop_15_24_alone',   sa.Float(),       nullable=True),
        sa.Column('pop_25_54_alone',   sa.Float(),       nullable=True),
        sa.Column('pop_55_79_alone',   sa.Float(),       nullable=True),
        sa.Column('pop_80p_alone',     sa.Float(),       nullable=True),
        # Familles
        sa.Column('families',          sa.Float(),       nullable=True),
        sa.Column('couples_with_children', sa.Float(),   nullable=True),
        sa.Column('single_parent',     sa.Float(),       nullable=True),
        sa.Column('couples_no_children', sa.Float(),     nullable=True),
        # Nombre d'enfants
        sa.Column('families_0_children', sa.Float(),    nullable=True),
        sa.Column('families_1_child',    sa.Float(),    nullable=True),
        sa.Column('families_2_children', sa.Float(),    nullable=True),
        sa.Column('families_3_children', sa.Float(),    nullable=True),
        sa.Column('families_4p_children', sa.Float(),   nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iris_code', 'year', name='uq_iris_families_iris_year'),
    )
    op.create_index('ix_iris_families_iris_year', 'iris_families', ['iris_code', 'year'])
    op.create_index('ix_iris_families_com_year',  'iris_families', ['com_code',  'year'])
    op.create_index('ix_iris_families_dep_code',  'iris_families', ['dep_code'])
    op.create_index('ix_iris_families_reg_code',  'iris_families', ['reg_code'])
    op.create_index('ix_iris_families_year',      'iris_families', ['year'])


def downgrade() -> None:
    op.drop_index('ix_iris_families_year',      table_name='iris_families')
    op.drop_index('ix_iris_families_reg_code',  table_name='iris_families')
    op.drop_index('ix_iris_families_dep_code',  table_name='iris_families')
    op.drop_index('ix_iris_families_com_year',  table_name='iris_families')
    op.drop_index('ix_iris_families_iris_year', table_name='iris_families')
    op.drop_table('iris_families')
