"""families_by_territory : enfants de moins de 6 ans selon l'activité des parents (2023)

Revision ID: a0c2e4f6b8d9
Revises: f8b0d2e4a6c7
Create Date: 2026-10-07

Source : tableau détaillé INSEE DS_RP_TD_FAMILLE_AGEENF_COMP (2023 uniquement), équivalent
du TD_FAM6 : nombre d'enfants de moins de 2 ans et de 2 à 5 ans, selon le type de famille
et l'activité des parents (en emploi / sans emploi). Valeurs officielles à toutes les échelles.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a0c2e4f6b8d9'
down_revision: Union[str, None] = 'f8b0d2e4a6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ['children_lt2_father_employed', 'children_lt2_father_not_employed', 'children_lt2_mother_employed', 'children_lt2_mother_not_employed', 'children_lt2_couple_both_employed', 'children_lt2_couple_man_only_employed', 'children_lt2_couple_woman_only_employed', 'children_lt2_couple_none_employed', 'children_2_5_father_employed', 'children_2_5_father_not_employed', 'children_2_5_mother_employed', 'children_2_5_mother_not_employed', 'children_2_5_couple_both_employed', 'children_2_5_couple_man_only_employed', 'children_2_5_couple_woman_only_employed', 'children_2_5_couple_none_employed']


def upgrade() -> None:
    for c in COLUMNS:
        op.add_column('families_by_territory', sa.Column(c, sa.Float(), nullable=True))


def downgrade() -> None:
    for c in COLUMNS:
        op.drop_column('families_by_territory', c)
