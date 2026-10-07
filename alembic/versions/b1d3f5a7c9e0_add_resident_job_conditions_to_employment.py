"""employment_by_territory : statut, contrat et temps partiel des actifs occupés résidents

Revision ID: b1d3f5a7c9e0
Revises: a0c2e4f6b8d9
Create Date: 2026-10-07

Source : INSEE DS_RP_ACTIVITE_PRINC (« Caractéristiques de l'emploi », 2012, 2017, 2023),
actifs occupés au lieu de résidence. Salariés en CDI / fonction publique (211) ou en contrat
à durée limitée (22T27 : CDD, intérim, emplois aidés, apprentissage, stage) ; temps partiel
par sexe et tranche d'âge. Valeurs officielles à toutes les échelles.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1d3f5a7c9e0'
down_revision: Union[str, None] = 'a0c2e4f6b8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ['res_workers', 'res_workers_men', 'res_workers_women', 'res_salaried', 'res_salaried_men', 'res_salaried_women', 'res_non_salaried', 'res_non_salaried_men', 'res_non_salaried_women', 'res_permanent', 'res_permanent_men', 'res_permanent_women', 'res_fixed_term', 'res_fixed_term_men', 'res_fixed_term_women', 'res_part_time', 'res_part_time_men', 'res_part_time_women', 'res_salaried_part_time', 'res_salaried_part_time_men', 'res_salaried_part_time_women', 'res_salaried_15_24', 'res_salaried_part_time_15_24', 'res_salaried_15_24_men', 'res_salaried_part_time_15_24_men', 'res_salaried_15_24_women', 'res_salaried_part_time_15_24_women', 'res_salaried_25_54', 'res_salaried_part_time_25_54', 'res_salaried_25_54_men', 'res_salaried_part_time_25_54_men', 'res_salaried_25_54_women', 'res_salaried_part_time_25_54_women', 'res_salaried_55_64', 'res_salaried_part_time_55_64', 'res_salaried_55_64_men', 'res_salaried_part_time_55_64_men', 'res_salaried_55_64_women', 'res_salaried_part_time_55_64_women', 'res_salaried_15_64', 'res_salaried_part_time_15_64', 'res_salaried_15_64_men', 'res_salaried_part_time_15_64_men', 'res_salaried_15_64_women', 'res_salaried_part_time_15_64_women']


def upgrade() -> None:
    for c in COLUMNS:
        op.add_column('employment_by_territory', sa.Column(c, sa.Float(), nullable=True))


def downgrade() -> None:
    for c in COLUMNS:
        op.drop_column('employment_by_territory', c)
