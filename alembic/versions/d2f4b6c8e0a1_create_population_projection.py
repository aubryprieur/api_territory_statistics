"""create population_projection (projections démographiques par commune, horizon 10 ans)

Revision ID: d2f4b6c8e0a1
Revises: c1e3a5b7d9f2
Create Date: 2026-11-02

Une ligne par commune : année de départ (2023), population de départ et résultats en JSONB (tranches d'âge par année
selon les scénarios tendance, sans migrations, natalité basse / haute ; naissances ; paramètres et test).
Import : scripts/import_population_projection.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'd2f4b6c8e0a1'
down_revision: Union[str, None] = 'c1e3a5b7d9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'population_projection',
        sa.Column('geo_code', sa.String(10), primary_key=True),
        sa.Column('base_year', sa.Integer(), nullable=False),
        sa.Column('population', sa.Float(), nullable=True),
        sa.Column('data', JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('population_projection')
