"""create equipment_types, equipment_by_territory, equipment_nearest (Base permanente des équipements 2025)

Revision ID: e1a3c5d7f9b2
Revises: d9f1b3c5e7a8
Create Date: 2026-10-08

Nombre d'équipements par type (TYPEQU) et par territoire (COM, ARM, EPCI, DEP, REG, FRANCE 'FM'), dont en quartier
prioritaire ; distance au service clé le plus proche pour les communes qui n'en ont pas.
Import : scripts/import_equipment_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1a3c5d7f9b2'
down_revision: Union[str, None] = 'd9f1b3c5e7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'equipment_types',
        sa.Column('typequ', sa.String(4), primary_key=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('domain', sa.String(1), nullable=True),
        sa.Column('domain_label', sa.String(), nullable=True),
        sa.Column('subdomain', sa.String(2), nullable=True),
        sa.Column('subdomain_label', sa.String(), nullable=True),
    )
    op.create_table(
        'equipment_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('typequ', sa.String(4), nullable=False),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.Column('count_qpv', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year', 'typequ'),
    )
    op.create_table(
        'equipment_nearest',
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('service', sa.String(40), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('nearest_code', sa.String(10), nullable=True),
        sa.Column('nearest_name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('geo_code', 'year', 'service'),
    )


def downgrade() -> None:
    op.drop_table('equipment_nearest')
    op.drop_table('equipment_by_territory')
    op.drop_table('equipment_types')
