"""create energy_poverty_by_territory (précarité énergétique logement, Géodip ONPE 2022)

Revision ID: b9d1f3a5c7e9
Revises: a8c0e2f4b6d8
Create Date: 2026-11-02

Une ligne par (geo_level, geo_code, year = 2022) : part des ménages en précarité énergétique logement selon le niveau
de vie (taux d'effort énergétique > 8 % et niveau de vie sous le 3e décile, modèle Prometheus du CGDD) et nombre de
ménages concernés. France (FM) = France métropolitaine (pas d'estimation outre-mer).
Import : scripts/import_energy_poverty_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9d1f3a5c7e9'
down_revision: Union[str, None] = 'a8c0e2f4b6d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'energy_poverty_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('energy_poverty_rate', sa.Float(), nullable=True),
        sa.Column('energy_poverty_households', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('energy_poverty_by_territory')
