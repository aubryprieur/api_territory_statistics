"""create immigration_by_territory (immigrés et étrangers — INSEE, recensement 2023)

Revision ID: c8e0a2b4d6f7
Revises: b7d9f1a3c5e6
Create Date: 2026-10-08

Une ligne par (geo_level, geo_code, year), millésime 2023 : population selon le statut d'immigré (âge, sexe, situation
d'activité, catégorie socioprofessionnelle) et selon la nationalité. geo_level ∈ COM, ARM, EPCI, DEP, REG,
FRANCE ('FM'). Import : scripts/import_immigration_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8e0a2b4d6f7'
down_revision: Union[str, None] = 'b7d9f1a3c5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['imm', 'imm_women', 'imm_lt15', 'imm_15_24', 'imm_25_54', 'imm_ge55', 'imm_employed_15p', 'imm_unemployed_15p', 'imm_retired_15p', 'imm_students_15p', 'imm_homemakers_15p', 'imm_other_inactive_15p', 'imm_employed_25_54', 'imm_women_25_54', 'imm_women_employed_25_54', 'imm_women_homemakers_25_54', 'imm_pcs1', 'imm_pcs2', 'imm_pcs3', 'imm_pcs4', 'imm_pcs5', 'imm_pcs6', 'nonimm', 'nonimm_women', 'nonimm_lt15', 'nonimm_15_24', 'nonimm_25_54', 'nonimm_ge55', 'nonimm_employed_15p', 'nonimm_unemployed_15p', 'nonimm_retired_15p', 'nonimm_students_15p', 'nonimm_homemakers_15p', 'nonimm_other_inactive_15p', 'nonimm_employed_25_54', 'nonimm_women_25_54', 'nonimm_women_employed_25_54', 'nonimm_women_homemakers_25_54', 'nonimm_pcs1', 'nonimm_pcs2', 'nonimm_pcs3', 'nonimm_pcs4', 'nonimm_pcs5', 'nonimm_pcs6', 'population', 'foreign', 'foreign_women', 'foreign_lt15', 'foreign_employed_15p', 'foreign_unemployed_15p', 'french', 'french_women', 'french_lt15', 'french_employed_15p', 'french_unemployed_15p']


def upgrade() -> None:
    op.create_table(
        'immigration_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('immigration_by_territory')
