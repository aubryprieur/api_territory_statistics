"""create revenues_by_territory (revenus et pauvreté — INSEE, Filosofi)

Revision ID: a6c8e0f2b4d5
Revises: f5b7d9e1a3c4
Create Date: 2026-10-08

Une ligne par (geo_level, geo_code, year), années 2017 à 2021 (chiffres clés Filosofi) et 2023 (nouvelle
diffusion : communes et EPCI limités au niveau de vie médian et au taux de pauvreté). Pas de millésime 2022.
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM'). Import : scripts/import_revenues_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a6c8e0f2b4d5'
down_revision: Union[str, None] = 'f5b7d9e1a3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['fiscal_households', 'fiscal_persons', 'median_living_standard', 'taxed_households_rate', 'poverty_rate', 'poverty_rate_ref_lt30', 'poverty_rate_ref_30_39', 'poverty_rate_ref_40_49', 'poverty_rate_ref_50_59', 'poverty_rate_ref_60_74', 'poverty_rate_ref_ge75', 'poverty_rate_owners', 'poverty_rate_tenants', 'share_activity_income', 'share_salaries', 'share_unemployment_benefits', 'share_self_employment', 'share_pensions', 'share_property_income', 'share_social_benefits', 'share_family_benefits', 'share_minimum_income', 'share_housing_benefits', 'share_taxes', 'd1', 'd9', 'interdecile_ratio', 'd2', 'd3', 'd4', 'd6', 'd7', 'd8', 'q1', 'q3', 'gini', 's80s20', 'interquartile_range', 'poverty_rate_ind_lt18', 'poverty_rate_ind_18_29', 'poverty_rate_ind_30_39', 'poverty_rate_ind_40_49', 'poverty_rate_ind_50_64', 'poverty_rate_ind_65_74', 'poverty_rate_ind_ge75', 'median_ind_lt18', 'median_ind_18_29', 'median_ind_30_39', 'median_ind_40_49', 'median_ind_50_64', 'median_ind_65_74', 'median_ind_ge75']


def upgrade() -> None:
    op.create_table(
        'revenues_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('revenues_by_territory')
