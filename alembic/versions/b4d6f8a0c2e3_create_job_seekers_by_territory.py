"""create job_seekers_by_territory (demandeurs d'emploi inscrits à France Travail — Dares, données communales)

Revision ID: b4d6f8a0c2e3
Revises: a3c5e7f9b1d2
Create Date: 2026-10-11

Une ligne par (geo_level, geo_code, year) : demandeurs d'emploi en catégories A, B, C au 4e trimestre (moyenne
trimestrielle, données brutes arrondies à 5 par la Dares), par sexe et tranche d'âge.
Import : scripts/import_job_seekers_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4d6f8a0c2e3'
down_revision: Union[str, None] = 'a3c5e7f9b1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['abc', 'abc_women', 'abc_men', 'abc_lt25', 'abc_25_49', 'abc_ge50']


def upgrade() -> None:
    op.create_table(
        'job_seekers_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('job_seekers_by_territory')
