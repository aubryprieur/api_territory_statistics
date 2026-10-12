"""create sports_by_territory (licences sportives — INJEP, diffusion Observatoire des territoires)

Revision ID: f3b5d7e9a1c2
Revises: e2a4c6e8f0b1
Create Date: 2026-10-12

Une ligne par (geo_level, geo_code, year) : licenciés pour 100 habitants (ensemble, 15-29 ans, 30-59 ans) et part
des filles / femmes parmi les licenciés (0-14, 15-29, 30-59, 60 ans ou plus), 2023.
Import : scripts/import_sports_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3b5d7e9a1c2'
down_revision: Union[str, None] = 'e2a4c6e8f0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['licence_rate', 'licence_rate_15_29', 'licence_rate_30_59', 'girls_share_0_14', 'women_share_15_29',
            'women_share_30_59', 'women_share_60p']


def upgrade() -> None:
    op.create_table(
        'sports_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('sports_by_territory')
