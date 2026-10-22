"""create fragilities_by_territory (Observatoire interrégimes des situations de fragilité, APL ANCT)

Revision ID: b3d5f7a9c1e2
Revises: a2c4e6f8b0d1
Create Date: 2026-10-22

Une ligne par (geo_level, geo_code, year = 2025) : recours aux soins, prévention, ALD, invalidité, C2S (pourcentages
publiés, sans effectifs), APL dentistes et médecins de moins de 65 ans (2024).
Import : scripts/import_fragilities_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3d5f7a9c1e2'
down_revision: Union[str, None] = 'a2c4e6f8b0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['no_gp_rate', 'ald_rate', 'invalidity_rate', 'c2s_rate', 'no_dentist_rate', 'no_colorectal_screening_rate',
            'no_cervical_screening_rate', 'no_mammography_rate', 'no_gynecologist_rate', 'no_flu_vaccine_65p_rate',
            'no_flu_vaccine_75p_rate', 'apl_dentists', 'apl_gp_under65']


def upgrade() -> None:
    op.create_table(
        'fragilities_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('fragilities_by_territory')
