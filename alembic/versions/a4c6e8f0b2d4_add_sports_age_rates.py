"""add licence_rate_0_14 and licence_rate_60p to sports_by_territory

Revision ID: a4c6e8f0b2d4
Revises: f3b5d7e9a1c2
Create Date: 2026-10-12

Licenciés de 0-14 ans pour 100 habitants de 0-14 ans, de 60 ans ou plus pour 100 habitants de 60 ans ou plus (INJEP 2023).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4c6e8f0b2d4'
down_revision: Union[str, None] = 'f3b5d7e9a1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sports_by_territory', sa.Column('licence_rate_0_14', sa.Float(), nullable=True))
    op.add_column('sports_by_territory', sa.Column('licence_rate_60p', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('sports_by_territory', 'licence_rate_60p')
    op.drop_column('sports_by_territory', 'licence_rate_0_14')
