"""create pass_sport_by_territory (pass Sport 2024, activations par commune de résidence)

Revision ID: e6a8c0d2f4b5
Revises: d5f7b9c1e3a4
Create Date: 2026-10-22

Une ligne par (geo_level, geo_code, year = 2024) : pass Sport activés (campagne juin 2024 - février 2025), dont 6-17 ans,
filles parmi les 6-17 ans, étudiants boursiers (Cnous), population de 6-17 ans (recensement) et taux de recours.
Import : scripts/import_pass_sport_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6a8c0d2f4b5'
down_revision: Union[str, None] = 'd5f7b9c1e3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['activations', 'activations_6_17', 'girls_6_17', 'students', 'pop_6_17', 'rate_6_17', 'girls_share_6_17']


def upgrade() -> None:
    op.create_table(
        'pass_sport_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('pass_sport_by_territory')
