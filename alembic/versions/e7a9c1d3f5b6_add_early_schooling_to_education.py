"""education_by_territory : scolarisation à 2 ans et à 3-5 ans

Revision ID: e7a9c1d3f5b6
Revises: d6f8b0c2e4a5
Create Date: 2026-10-07

Ajoute population et population scolarisée à 2 ans et à 3-5 ans :
  - 2023 : tableaux détaillés INSEE DS_RP_TD_EDUCATION_PRINC (scolarisés par âge fin)
           et DS_RP_TD_POPULATION_AGESEX_PRINC (population par âge fin), valeurs officielles ;
  - 2017 : table schooling_summary (tableau détaillé FOR1 2017, communes), agrégée par
           EPCI / département / région via geo_codes ;
  - 2012 : non disponible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7a9c1d3f5b6'
down_revision: Union[str, None] = 'd6f8b0c2e4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ["pop_2", "enrolled_2", "pop_3_5", "enrolled_3_5"]


def upgrade() -> None:
    for c in COLUMNS:
        op.add_column('education_by_territory', sa.Column(c, sa.Float(), nullable=True))


def downgrade() -> None:
    for c in COLUMNS:
        op.drop_column('education_by_territory', c)
