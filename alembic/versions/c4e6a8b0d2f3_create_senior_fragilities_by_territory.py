"""create senior_fragilities_by_territory (Observatoire des situations de fragilité, retraités et seniors interrégime)

Revision ID: c4e6a8b0d2f3
Revises: b3d5f7a9c1e2
Create Date: 2026-10-22

Une ligne par (geo_level, geo_code, year = 2025) : scores de fragilité, part des retraités à risque, ressources (minimum
vieillesse, CSG), parcours (réversion, invalidité/inaptitude, carrière incomplète), santé des 55 ans ou plus (C2S non
participative, non-recours aux soins, médecin traitant, ALD), nombre de retraités 2025 et évolution depuis 2017.
Import : scripts/import_senior_fragilities_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e6a8b0d2f3'
down_revision: Union[str, None] = 'b3d5f7a9c1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['social_fragility_score', 'care_nonuse_score', 'at_risk_share', 'at_risk_count', 'retirees_count',
            'retirees_change_rate', 'min_old_age_rate', 'csg_exempt_rate', 'csg_low_rate', 'survivor_pension_rate',
            'invalidity_inaptitude_rate', 'incomplete_career_rate', 'css_free_rate', 'no_care_rate', 'no_gp_rate',
            'ald_rate']


def upgrade() -> None:
    op.create_table(
        'senior_fragilities_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('senior_fragilities_by_territory')
