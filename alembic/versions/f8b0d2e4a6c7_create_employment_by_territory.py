"""create employment_by_territory (emploi, activité, chômage, emplois, navettes — RP INSEE)

Revision ID: f8b0d2e4a6c7
Revises: e7a9c1d3f5b6
Create Date: 2026-10-07

Une ligne par (geo_level, geo_code, year), valeurs officielles INSEE (sans agrégation) issues de :
  - DS_RP_EMPLOI_LR_PRINC : population, actifs, actifs occupés, chômeurs, inactifs (lieu de résidence)
  - DS_RP_EMPLOI_LR_COMP  : actifs et actifs occupés de 15-64 ans par catégorie socioprofessionnelle
  - DS_RP_EMPLOI_LT_PRINC : emplois au lieu de travail (statut, temps partiel, femmes)
  - DS_RP_EMPLOI_LT_COMP  : emplois au lieu de travail par secteur d'activité
  - DS_RP_NAVETTES_PRINC  : actifs occupés selon le lieu de travail et le mode de transport
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM'). Millésimes : 2012, 2017, 2023.
Import : scripts/import_employment_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8b0d2e4a6c7'
down_revision: Union[str, None] = 'e7a9c1d3f5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['pop_15_64', 'active_15_64', 'employed_15_64', 'unemployed_15_64', 'pop_15_64_men', 'active_15_64_men', 'employed_15_64_men', 'unemployed_15_64_men', 'pop_15_64_women', 'active_15_64_women', 'employed_15_64_women', 'unemployed_15_64_women', 'pop_15_24', 'active_15_24', 'employed_15_24', 'unemployed_15_24', 'pop_15_24_men', 'active_15_24_men', 'employed_15_24_men', 'unemployed_15_24_men', 'pop_15_24_women', 'active_15_24_women', 'employed_15_24_women', 'unemployed_15_24_women', 'pop_25_54', 'active_25_54', 'employed_25_54', 'unemployed_25_54', 'pop_25_54_men', 'active_25_54_men', 'employed_25_54_men', 'unemployed_25_54_men', 'pop_25_54_women', 'active_25_54_women', 'employed_25_54_women', 'unemployed_25_54_women', 'pop_55_64', 'active_55_64', 'employed_55_64', 'unemployed_55_64', 'pop_55_64_men', 'active_55_64_men', 'employed_55_64_men', 'unemployed_55_64_men', 'pop_55_64_women', 'active_55_64_women', 'employed_55_64_women', 'unemployed_55_64_women', 'retired_15_64', 'students_15_64', 'homemakers_15_64', 'other_inactive_15_64', 'retired_15_64_men', 'students_15_64_men', 'homemakers_15_64_men', 'other_inactive_15_64_men', 'retired_15_64_women', 'students_15_64_women', 'homemakers_15_64_women', 'other_inactive_15_64_women', 'employed_15_plus', 'active_no_diploma', 'unemployed_no_diploma', 'active_bepc', 'unemployed_bepc', 'active_cap_bep', 'unemployed_cap_bep', 'active_bac', 'unemployed_bac', 'active_bac2', 'unemployed_bac2', 'active_bac3_4', 'unemployed_bac3_4', 'active_bac5_plus', 'unemployed_bac5_plus', 'active_pcs_1', 'employed_pcs_1', 'active_pcs_2', 'employed_pcs_2', 'active_pcs_3', 'employed_pcs_3', 'active_pcs_4', 'employed_pcs_4', 'active_pcs_5', 'employed_pcs_5', 'active_pcs_6', 'employed_pcs_6', 'jobs', 'jobs_salaried', 'jobs_non_salaried', 'jobs_salaried_part_time', 'jobs_women', 'jobs_agriculture', 'jobs_industry', 'jobs_construction', 'jobs_trade_services', 'jobs_public_services', 'workers', 'work_in_commune', 'work_other_commune_dep', 'work_other_dep_region', 'work_other_region', 'work_abroad_overseas', 'commute_none', 'commute_walk', 'commute_bike', 'commute_two_wheels', 'commute_car', 'commute_public']


def upgrade() -> None:
    op.create_table(
        'employment_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('employment_by_territory')
