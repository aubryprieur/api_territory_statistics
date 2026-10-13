"""create tax_households_by_territory (DGFiP — IRCOM, foyers fiscaux par commune)

Revision ID: e8a0c2d4f6b9
Revises: d7f9b1c3e5a8
Create Date: 2026-10-13

Une ligne par (geo_level, geo_code, year = année des revenus : 2021, 2024) : foyers fiscaux, revenu fiscal de
référence, impôt net, foyers imposés, foyers avec salaires, avec retraites, foyers par tranche de RFR.
Import : scripts/import_tax_households_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e8a0c2d4f6b9'
down_revision: Union[str, None] = 'd7f9b1c3e5a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['households', 'rfr', 'net_tax', 'taxed_households', 'wage_households', 'pension_households',
            'hh_0_10k', 'hh_10_12k', 'hh_12_15k', 'hh_15_20k', 'hh_20_30k', 'hh_30_50k', 'hh_50_100k', 'hh_100k_plus']


def upgrade() -> None:
    op.create_table(
        'tax_households_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('tax_households_by_territory')
