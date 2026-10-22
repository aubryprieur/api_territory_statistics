"""create elderly_care_by_territory (BPE 2025 : hébergement et services à domicile pour personnes âgées)

Revision ID: d5f7b9c1e3a4
Revises: c4e6a8b0d2f3
Create Date: 2026-10-22

Une ligne par (geo_level, geo_code, year = 2025) : établissements d'hébergement pour personnes âgées (D401 : Ehpad,
résidences autonomie…) et leurs places, services de soins (D402) et d'aide (D403) à domicile implantés, population de
75 ans ou plus (recensement 2023) et places pour 1 000 personnes de 75 ans ou plus.
Import : scripts/import_elderly_care_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5f7b9c1e3a4'
down_revision: Union[str, None] = 'c4e6a8b0d2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['housing_facilities', 'housing_places', 'housing_no_capacity', 'home_nursing_services',
            'home_help_services', 'pop_75p', 'places_per_1000_75p']


def upgrade() -> None:
    op.create_table(
        'elderly_care_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('elderly_care_by_territory')
