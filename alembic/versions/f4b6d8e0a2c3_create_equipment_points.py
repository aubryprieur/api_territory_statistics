"""create equipment_points (localisation des équipements de la BPE utiles aux enfants et aux jeunes)

Revision ID: f4b6d8e0a2c3
Revises: e3a5c7d9f1b2
Create Date: 2026-11-06

Une ligne par équipement géolocalisé de la Base permanente des équipements (BPE 2025, INSEE) pour une sélection de
types (app/services/equipment_points_service.py, GROUPS) : type, commune, EPCI, nom (raison sociale), coordonnées WGS84,
quartier prioritaire, qualité de géolocalisation. Import : scripts/import_equipment_points.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4b6d8e0a2c3'
down_revision: Union[str, None] = 'e3a5c7d9f1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'equipment_points',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('typequ', sa.String(4), nullable=False),
        sa.Column('depcom', sa.String(5), nullable=False),
        sa.Column('epci', sa.String(9), nullable=True),
        sa.Column('commune_name', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('qpv', sa.Boolean(), nullable=True),
        sa.Column('quality', sa.String(2), nullable=True),
    )
    op.create_index('ix_equipment_points_depcom', 'equipment_points', ['depcom'])
    op.create_index('ix_equipment_points_epci', 'equipment_points', ['epci'])
    op.create_index('ix_equipment_points_lat_lon', 'equipment_points', ['lat', 'lon'])


def downgrade() -> None:
    op.drop_table('equipment_points')
