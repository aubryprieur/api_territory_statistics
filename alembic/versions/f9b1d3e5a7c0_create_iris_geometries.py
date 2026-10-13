"""create iris_geometries (contours IRIS simplifiés, découpage 2024)

Revision ID: f9b1d3e5a7c0
Revises: e8a0c2d4f6b9
Create Date: 2026-10-13

Une ligne par IRIS : commune (ou arrondissement), commune entière, nom, type, point d'étiquette et contour GeoJSON
simplifié (WGS84). Préparation : scripts/build_iris_geometries.py ; import : scripts/import_iris_geometries.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f9b1d3e5a7c0'
down_revision: Union[str, None] = 'e8a0c2d4f6b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_geometries',
        sa.Column('iris_code', sa.String(9), primary_key=True),
        sa.Column('com_code', sa.String(5), nullable=False),
        sa.Column('com_parent', sa.String(5), nullable=False),
        sa.Column('iris_name', sa.String(255)),
        sa.Column('iris_type', sa.String(50)),
        sa.Column('label_lon', sa.Float()),
        sa.Column('label_lat', sa.Float()),
        sa.Column('geometry', sa.Text(), nullable=False),
    )
    op.create_index('ix_iris_geometries_com_parent', 'iris_geometries', ['com_parent'])
    op.create_index('ix_iris_geometries_com_code', 'iris_geometries', ['com_code'])


def downgrade() -> None:
    op.drop_index('ix_iris_geometries_com_code', 'iris_geometries')
    op.drop_index('ix_iris_geometries_com_parent', 'iris_geometries')
    op.drop_table('iris_geometries')
