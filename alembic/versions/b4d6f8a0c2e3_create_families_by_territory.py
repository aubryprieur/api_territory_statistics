"""create families_by_territory (familles RP INSEE, toutes échelles)

Revision ID: b4d6f8a0c2e3
Revises: a3c5d7e9f1b2
Create Date: 2026-10-07

Une ligne par (geo_level, geo_code, year), alimentée directement par le
fichier INSEE DS_RP_FAMILLE_COMP (valeurs officielles, sans agrégation) :
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE (code 'FM' = France métropolitaine).
Millésimes : 2012, 2017, 2023. Import : scripts/import_families_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4d6f8a0c2e3'
down_revision: Union[str, None] = 'a3c5d7e9f1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = [
    "total_families",            # TFN=_T, NCH=_T
    "couples_with_children",     # TFN=22
    "couples_without_children",  # TFN=21
    "single_parent_families",    # TFN=1
    "single_fathers",            # TFN=11
    "single_mothers",            # TFN=12
    "blended_families",          # TFN=220 (familles recomposées, 2023 uniquement)
    "traditional_families",      # TFN=223 (familles traditionnelles, 2023 uniquement)
    "families_0_children",       # NCH=CH0_Y_LT25
    "families_1_child",          # NCH=CH1_Y_LT25
    "families_2_children",       # NCH=CH2_Y_LT25
    "families_3_children",       # NCH=CH3_Y_LT25
    "families_4_plus_children",  # NCH=CH_GE4_Y_LT25
]


def upgrade() -> None:
    op.create_table(
        'families_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('families_by_territory')
