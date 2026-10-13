"""create business_creations_by_territory (Insee, SIDE — créations d'entreprises par commune)

Revision ID: d7f9b1c3e5a8
Revises: c6e8f0a2b4d7
Create Date: 2026-10-13

Une ligne par (geo_level, geo_code, year), 2019-2025 : créations d'entreprises (total, entreprises individuelles,
sociétés, avec salariés) et par grand secteur.
Import : scripts/import_business_creations_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7f9b1c3e5a8'
down_revision: Union[str, None] = 'c6e8f0a2b4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['created', 'created_individual', 'created_company', 'created_employer', 'sector_industry',
            'sector_construction', 'sector_trade', 'sector_business_services', 'sector_personal_services']


def upgrade() -> None:
    op.create_table(
        'business_creations_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Integer(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('business_creations_by_territory')
