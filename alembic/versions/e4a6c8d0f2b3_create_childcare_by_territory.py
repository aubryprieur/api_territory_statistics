"""create childcare_by_territory (accueil du jeune enfant — Cnaf, data.caf.fr)

Revision ID: e4a6c8d0f2b3
Revises: d3f5a7b9c1e2
Create Date: 2026-10-08

Une ligne par (geo_level, geo_code, year), années 2017 à 2023 : places et taux de couverture
(places pour 100 enfants de moins de 3 ans) par mode d'accueil, valeurs publiées par la Cnaf.
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FE' = France entière hors Mayotte).
source : 'cnaf_detail' (fichiers détaillés) ou 'cnaf_tauxcouv' (taux global seul, communes 2020-2021).
Import : scripts/import_childcare_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4a6c8d0f2b3'
down_revision: Union[str, None] = 'd3f5a7b9c1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['places_eaje_psu', 'places_eaje_hors_psu', 'places_eaje', 'places_preschool', 'places_childminder', 'places_home_care', 'places_individual', 'places_total', 'rate_eaje_psu', 'rate_eaje_hors_psu', 'rate_eaje', 'rate_preschool', 'rate_childminder', 'rate_home_care', 'rate_individual', 'rate_global']


def upgrade() -> None:
    op.create_table(
        'childcare_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.Column('source', sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('childcare_by_territory')
