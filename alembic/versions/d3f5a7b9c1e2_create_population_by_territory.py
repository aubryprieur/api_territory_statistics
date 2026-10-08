"""create population_by_territory et population_history_by_territory (population — RP INSEE)

Revision ID: d3f5a7b9c1e2
Revises: c2e4f6a8b0d1
Create Date: 2026-10-08

population_by_territory : une ligne par (geo_level, geo_code, year), millésimes 2012, 2017, 2023 :
  - DS_RP_POPULATION_PRINC : population par grande tranche d'âge et sexe
  - DS_RP_POPULATION_COMP  : 15 ans ou plus par catégorie socioprofessionnelle
  - DS_RP_MIGRES_PRINC     : lieu de résidence un an auparavant
  - DS_RP_TD_POPULATION_AGESEX_PRINC (2023) : pyramide des âges, tranches de l'enfance
population_history_by_territory : recensements 1968 à 2023 (DS_RP_SERIE_HISTORIQUE).
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM'). Import : scripts/import_population_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3f5a7b9c1e2'
down_revision: Union[str, None] = 'c2e4f6a8b0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['pop', 'pop_women', 'pop_men', 'pop_lt15', 'pop_lt15_women', 'pop_lt15_men', 'pop_15_24', 'pop_15_24_women', 'pop_15_24_men', 'pop_25_39', 'pop_25_39_women', 'pop_25_39_men', 'pop_40_54', 'pop_40_54_women', 'pop_40_54_men', 'pop_55_64', 'pop_55_64_women', 'pop_55_64_men', 'pop_65_79', 'pop_65_79_women', 'pop_65_79_men', 'pop_ge80', 'pop_ge80_women', 'pop_ge80_men', 'pop_ge65', 'pop_ge65_women', 'pop_ge65_men', 'pop_lt20', 'pop_lt20_women', 'pop_lt20_men', 'pop_20_64', 'pop_20_64_women', 'pop_20_64_men', 'pop_15p', 'pcs_1', 'pcs_2', 'pcs_3', 'pcs_4', 'pcs_5', 'pcs_6', 'pcs_7', 'pcs_9', 'mig_total', 'mig_same_dwelling', 'mig_same_commune', 'mig_other_commune', 'mig_same_department', 'mig_same_region', 'mig_other_region', 'mig_overseas', 'mig_abroad', 'mig_other_commune_1_14', 'mig_other_commune_15_24', 'mig_other_commune_25_54', 'mig_other_commune_ge55', 'pyr_men_0_4', 'pyr_women_0_4', 'pyr_men_5_9', 'pyr_women_5_9', 'pyr_men_10_14', 'pyr_women_10_14', 'pyr_men_15_19', 'pyr_women_15_19', 'pyr_men_20_24', 'pyr_women_20_24', 'pyr_men_25_29', 'pyr_women_25_29', 'pyr_men_30_34', 'pyr_women_30_34', 'pyr_men_35_39', 'pyr_women_35_39', 'pyr_men_40_44', 'pyr_women_40_44', 'pyr_men_45_49', 'pyr_women_45_49', 'pyr_men_50_54', 'pyr_women_50_54', 'pyr_men_55_59', 'pyr_women_55_59', 'pyr_men_60_64', 'pyr_women_60_64', 'pyr_men_65_69', 'pyr_women_65_69', 'pyr_men_70_74', 'pyr_women_70_74', 'pyr_men_75_79', 'pyr_women_75_79', 'pyr_men_80_84', 'pyr_women_80_84', 'pyr_men_85_89', 'pyr_women_85_89', 'pyr_men_90_94', 'pyr_women_90_94', 'pyr_men_ge95', 'pyr_women_ge95', 'age_0_2', 'age_3_5', 'age_6_10', 'age_11_14', 'age_15_17', 'age_18_24']
HISTORY = ['population', 'births', 'deaths', 'dwellings', 'dwellings_main', 'dwellings_secondary', 'dwellings_vacant', 'households_population', 'area_km2']


def _create(name, measures):
    op.create_table(
        name,
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in measures],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def upgrade() -> None:
    _create('population_by_territory', MEASURES)
    _create('population_history_by_territory', HISTORY)


def downgrade() -> None:
    op.drop_table('population_history_by_territory')
    op.drop_table('population_by_territory')
