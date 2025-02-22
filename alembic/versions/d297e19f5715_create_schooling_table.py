"""create_schooling_table

Revision ID: d297e19f5715
Revises: ae63584ec179
Create Date: 2025-02-21 10:28:49.995505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd297e19f5715'
down_revision: Union[str, None] = 'ae63584ec179'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'schooling',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('geo_code', sa.String(10), nullable=False, index=True),
        sa.Column('year', sa.Integer(), nullable=False, index=True),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('sex', sa.Integer(), nullable=False),
        sa.Column('education_status', sa.String(1), nullable=True),
        sa.Column('number', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

def downgrade() -> None:
    op.drop_table('schooling')
