"""create delinquency_by_territory (crimes et délits enregistrés — SSMSI, 2016-2025)

Revision ID: f2b4d6e8a0c1
Revises: e1a3c5d7f9b2
Create Date: 2026-10-09

Une ligne par (geo_level, geo_code, year) : pour chaque indicateur, nombre, taux pour 1 000 habitants (logements pour
les cambriolages) et diffusion (les petits effectifs communaux ne sont pas diffusés). COM, ARM, EPCI (somme des
communes), DEP, REG (bases SSMSI), FRANCE ('FM' = somme des départements de métropole).
Import : scripts/import_delinquency_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2b4d6e8a0c1'
down_revision: Union[str, None] = 'e1a3c5d7f9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDICATORS = ['homicide', 'attempted_homicide', 'intrafamily_violence', 'other_physical_violence', 'sexual_violence', 'armed_robbery', 'violent_theft', 'theft_without_violence', 'burglary', 'vehicle_theft', 'theft_from_vehicle', 'vehicle_accessory_theft', 'vandalism', 'drug_use', 'drug_use_afd', 'drug_use_non_afd', 'drug_trafficking', 'fraud']


def upgrade() -> None:
    columns = []
    for ind in INDICATORS:
        columns += [sa.Column(f"{ind}_count", sa.Float(), nullable=True),
                    sa.Column(f"{ind}_rate", sa.Float(), nullable=True),
                    sa.Column(f"{ind}_diffused", sa.Boolean(), nullable=True)]
    op.create_table(
        'delinquency_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('population', sa.Float(), nullable=True),
        sa.Column('dwellings', sa.Float(), nullable=True),
        *columns,
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('delinquency_by_territory')
