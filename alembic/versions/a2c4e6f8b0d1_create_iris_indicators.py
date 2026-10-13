"""create iris_indicators (indicateurs IRIS hors recensement, format long)

Revision ID: a2c4e6f8b0d1
Revises: f9b1d3e5a7c0
Create Date: 2026-10-13

Une ligne par (geo_level IRIS|COM, geo_code, year, indicator) : value (indicateur non additif : médiane, taux), count et
total (indicateur additif). Sources : Filosofi IRIS, C2S (Cnam), RPLS IRIS, demandeurs d'emploi IRIS.
Import : scripts/import_iris_indicators.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2c4e6f8b0d1'
down_revision: Union[str, None] = 'f9b1d3e5a7c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_indicators',
        sa.Column('geo_level', sa.String(5), nullable=False),
        sa.Column('geo_code', sa.String(9), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('indicator', sa.String(40), nullable=False),
        sa.Column('value', sa.Float()),
        sa.Column('count', sa.Float()),
        sa.Column('total', sa.Float()),
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year', 'indicator'),
    )
    op.create_index('ix_iris_indicators_indicator_code', 'iris_indicators', ['indicator', 'geo_code'])


def downgrade() -> None:
    op.drop_index('ix_iris_indicators_indicator_code', 'iris_indicators')
    op.drop_table('iris_indicators')
