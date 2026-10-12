"""create construction_by_territory (SDES — Sitadel, logements autorisés et commencés par type)

Revision ID: c6e8f0a2b4d7
Revises: b5d7f9a1c3e6
Create Date: 2026-10-12

Une ligne par (geo_level, geo_code, year), 2013-2025 : logements autorisés et commencés (total, individuel pur,
individuel groupé, collectif, résidence). Commencés 2025 non publiés (NULL).
Import : scripts/import_construction_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c6e8f0a2b4d7'
down_revision: Union[str, None] = 'b5d7f9a1c3e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = [f"{k}_{t}" for k in ("authorised", "started")
            for t in ("total", "ind_pure", "ind_group", "collective", "residence")]


def upgrade() -> None:
    op.create_table(
        'construction_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Integer(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('construction_by_territory')
