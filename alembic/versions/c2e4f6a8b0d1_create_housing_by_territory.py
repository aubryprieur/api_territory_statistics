"""create housing_by_territory (logement — RP INSEE)

Revision ID: c2e4f6a8b0d1
Revises: b1d3f5a7c9e0
Create Date: 2026-10-07

Une ligne par (geo_level, geo_code, year), valeurs officielles INSEE (sans agrégation) issues de :
  - DS_RP_LOGEMENT_PRINC : parc de logements, résidences principales par taille, statut d'occupation,
    ancienneté d'emménagement, chauffage, voitures, stationnement, période de construction
  - DS_RP_LOGEMENT_COMP  : indicateur de peuplement (suroccupation / sous-occupation)
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM'). Millésimes : 2012, 2017, 2023.
Import : scripts/import_housing_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2e4f6a8b0d1'
down_revision: Union[str, None] = 'b1d3f5a7c9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['dwellings', 'dwellings_main', 'dwellings_secondary', 'dwellings_vacant', 'dwellings_houses', 'dwellings_apartments', 'main_houses', 'main_apartments', 'main_r1', 'main_r2', 'main_r3', 'main_r4', 'main_r5p', 'main_rooms', 'main_owners', 'main_tenants', 'main_tenants_private', 'main_tenants_furnished', 'main_tenants_social', 'main_free', 'pop_main', 'pop_owners', 'pop_tenants', 'pop_tenants_social', 'stay_lt2', 'stay_2_4', 'stay_5_9', 'stay_10_19', 'stay_20_29', 'stay_ge30', 'stay_years', 'stay_years_owners', 'stay_years_tenants', 'stay_years_social', 'heat_town_gas', 'heat_oil', 'heat_electric', 'heat_bottled_gas', 'heat_other', 'with_parking', 'cars_0', 'cars_1', 'cars_2p', 'built_lt1919', 'built_1919_1945', 'built_1946_1970', 'built_1971_1990', 'built_1991_2005', 'built_2006_plus', 'occ_total', 'occ_over_severe', 'occ_over_moderate', 'occ_standard', 'occ_under_moderate', 'occ_under_severe', 'occ_under_very_severe', 'built_before_1946', 'built_1946_1990', 'built_after_1990', 'built_known']


def upgrade() -> None:
    op.create_table(
        'housing_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('housing_by_territory')
