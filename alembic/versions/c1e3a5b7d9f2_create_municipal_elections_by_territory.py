"""create municipal_elections_by_territory (élections municipales, 1er tour)

Revision ID: c1e3a5b7d9f2
Revises: b9d1f3a5c7e9
Create Date: 2026-11-02

Une ligne par (geo_level, geo_code, year = année de l'élection) : inscrits, votants, exprimés, blancs, nuls au 1er tour
et taux de participation (votants / inscrits). Communes : résultats du ministère de l'Intérieur ; EPCI, départements,
régions, France métropolitaine (FM) : sommes des communes.
Import : scripts/import_municipal_elections_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1e3a5b7d9f2'
down_revision: Union[str, None] = 'b9d1f3a5c7e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['registered', 'voters', 'expressed', 'blank', 'null', 'turnout_rate', 'blank_null_rate']


def upgrade() -> None:
    op.create_table(
        'municipal_elections_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('municipal_elections_by_territory')
