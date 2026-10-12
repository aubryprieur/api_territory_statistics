"""create associations_by_territory (RNA — associations en activité par catégorie, créations annuelles)

Revision ID: b5d7f9a1c3e6
Revises: a4c6e8f0b2d4
Create Date: 2026-10-12

Une ligne par (geo_level, geo_code, year) : year 2026 = associations en activité au 1er octobre 2026 (total et
11 grandes catégories) ; years 2010-2025 = créations d'associations dans l'année.
Import : scripts/import_associations_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5d7f9a1c3e6'
down_revision: Union[str, None] = 'a4c6e8f0b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['active', 'theme_sport', 'theme_culture', 'theme_leisure', 'theme_social', 'theme_education',
            'theme_friendly', 'theme_civic', 'theme_environment', 'theme_economy', 'theme_religion', 'theme_other',
            'created']


def upgrade() -> None:
    op.create_table(
        'associations_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Integer(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('associations_by_territory')
