"""add age bands to iris_population (DS_RP_POPULATION_PRINC_IRIS_2023 : moins de 20 ans, 65 ans ou plus, moins de 2 ans…)

Revision ID: a5c7e9b1d3f4
Revises: f4b6d8e0a2c3
Create Date: 2026-11-09

Tranches publiées par l'Insee à l'IRIS dans le nouveau format (2023) et absentes des bases infracommunales historiques :
moins de 20 ans, 65 ans ou plus, moins de 2 ans, 2-5 ans, 11-14 ans, 15-17 ans. Renseignées pour 2023 seulement.
Import : scripts/import_iris_population_ages.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a5c7e9b1d3f4'
down_revision: Union[str, None] = 'f4b6d8e0a2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ["pop_lt20", "pop_ge65", "pop_lt2", "pop_2_5", "pop_11_14", "pop_15_17"]


def upgrade() -> None:
    for c in COLUMNS:
        op.add_column('iris_population', sa.Column(c, sa.Float(), nullable=True))


def downgrade() -> None:
    for c in COLUMNS:
        op.drop_column('iris_population', c)
