"""add_iris_name_dep_reg_to_iris_population

Revision ID: 9f583757ca4e
Revises: caeeaef40243
Create Date: 2026-05-03 14:47:06.562685

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f583757ca4e'
down_revision: Union[str, None] = 'caeeaef40243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('iris_population', sa.Column('iris_name', sa.String(255), nullable=True))
    op.add_column('iris_population', sa.Column('dep_code',  sa.String(3),   nullable=True))
    op.add_column('iris_population', sa.Column('reg_code',  sa.String(2),   nullable=True))
    op.create_index('ix_iris_population_dep_code', 'iris_population', ['dep_code'])
    op.create_index('ix_iris_population_reg_code', 'iris_population', ['reg_code'])


def downgrade() -> None:
    op.drop_index('ix_iris_population_reg_code', table_name='iris_population')
    op.drop_index('ix_iris_population_dep_code', table_name='iris_population')
    op.drop_column('iris_population', 'reg_code')
    op.drop_column('iris_population', 'dep_code')
    op.drop_column('iris_population', 'iris_name')

