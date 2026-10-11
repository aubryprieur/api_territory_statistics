"""create sdg_indicators_by_territory (indicateurs de développement durable sélectionnés — INSEE / SDES, base ODD)

Revision ID: a3c5e7f9b1d2
Revises: f2b4d6e8a0c1
Create Date: 2026-10-11

Une ligne par (geo_level, geo_code, year) : insertion des jeunes, chômage de longue durée, écart d'emploi
femmes-hommes, économie sociale et solidaire, accessibilité aux médecins généralistes (APL), déplacements
domicile-travail, logements sociaux et vacants, participation électorale. Import : scripts/import_sdg_indicators_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c5e7f9b1d2'
down_revision: Union[str, None] = 'f2b4d6e8a0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['young_neet_rate', 'young_no_diploma_rate', 'long_term_unemployed_share', 'employment_gap_women_men', 'employment_gap_women_men_25_54', 'ess_jobs_share', 'gp_accessibility', 'commute_minutes', 'commute_km', 'commute_car_share', 'commute_public_transport_share', 'commute_walk_share', 'commute_bike_share', 'commute_two_wheels_share', 'commute_no_transport_share', 'social_housing_share', 'vacant_housing_share', 'presidential_turnout']


def upgrade() -> None:
    op.create_table(
        'sdg_indicators_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('sdg_indicators_by_territory')
