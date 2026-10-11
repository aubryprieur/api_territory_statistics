"""create social_housing_by_territory (parc locatif social — SDES, RPLS au 1er janvier 2025)

Revision ID: d1f3a5c7e9b2
Revises: c9e1a3b5d7f0
Create Date: 2026-10-11

Une ligne par (geo_level, geo_code, year) : séries 2013 → 2025 (parc social, mises en service, vacance, mobilité,
loyer moyen au m²) et structure du parc au 1er janvier 2025 (densité, QPV, type, pièces, financement, âge, DPE,
sorties). Import : scripts/import_social_housing_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1f3a5c7e9b2'
down_revision: Union[str, None] = 'c9e1a3b5d7f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['social_dwellings', 'new_dwellings', 'vacancy_rate', 'vacancy_3m_rate', 'mobility_rate', 'avg_rent_m2', 'rented', 'vacant', 'offered', 'density', 'in_qpv', 'individual', 'collective', 'rooms_1', 'rooms_2', 'rooms_3', 'rooms_4', 'rooms_5p', 'fin_plai', 'fin_plus_after_77', 'fin_plus_before_77', 'fin_pls', 'fin_pli', 'avg_age', 'age_lt10', 'age_ge60', 'sold', 'demolished', 'dpe_done', 'dpe_ab', 'dpe_fg']


def upgrade() -> None:
    op.create_table(
        'social_housing_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('social_housing_by_territory')
