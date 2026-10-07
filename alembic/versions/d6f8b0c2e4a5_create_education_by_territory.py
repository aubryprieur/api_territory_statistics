"""create education_by_territory (scolarisation et diplômes RP INSEE, toutes échelles)

Revision ID: d6f8b0c2e4a5
Revises: c5e7a9b1d3f4
Create Date: 2026-10-07

Une ligne par (geo_level, geo_code, year), alimentée directement par les fichiers INSEE
DS_RP_EDUCATION_PRINC (population et population scolarisée par âge et sexe) et
DS_RP_DIPLOMES_PRINC (population de 15 ans ou plus non scolarisée par diplôme et sexe).
Valeurs officielles, sans agrégation. geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM').
Millésimes : 2012, 2017, 2023. Import : scripts/import_education_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6f8b0c2e4a5'
down_revision: Union[str, None] = 'c5e7a9b1d3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['pop_2_5', 'enrolled_2_5', 'pop_6_10', 'enrolled_6_10', 'pop_11_14', 'enrolled_11_14', 'pop_15_17', 'enrolled_15_17', 'pop_18_24', 'enrolled_18_24', 'pop_25_29', 'enrolled_25_29', 'pop_30_plus', 'enrolled_30_plus', 'pop_15_17_men', 'enrolled_15_17_men', 'pop_15_17_women', 'enrolled_15_17_women', 'pop_18_24_men', 'enrolled_18_24_men', 'pop_18_24_women', 'enrolled_18_24_women', 'non_enrolled_15_plus', 'no_diploma', 'bepc', 'cap_bep', 'bac', 'higher_education', 'bac2', 'bac3_4', 'bac5_plus', 'bac3_plus', 'non_enrolled_15_plus_men', 'no_diploma_men', 'higher_education_men', 'non_enrolled_15_plus_women', 'no_diploma_women', 'higher_education_women']


def upgrade() -> None:
    op.create_table(
        'education_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('education_by_territory')
