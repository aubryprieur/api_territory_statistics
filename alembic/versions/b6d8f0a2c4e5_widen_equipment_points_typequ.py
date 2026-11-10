"""widen equipment_points.typequ (services de l'Annuaire de l'administration, DILA : « DILA:mission_locale »…)

Revision ID: b6d8f0a2c4e5
Revises: a5c7e9b1d3f4
Create Date: 2026-11-10

Les services publics locaux de l'Annuaire de l'administration (DILA, Base de données locales de Service-Public.fr) sont
ajoutés à equipment_points avec un type préfixé « DILA: » (le code pivot de l'annuaire), d'où une colonne plus large.
Import : scripts/import_annuaire_points.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6d8f0a2c4e5'
down_revision: Union[str, None] = 'a5c7e9b1d3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("equipment_points", "typequ", type_=sa.String(40), existing_type=sa.String(4), existing_nullable=False)
    op.create_index("ix_equipment_points_typequ", "equipment_points", ["typequ"])


def downgrade() -> None:
    op.drop_index("ix_equipment_points_typequ", table_name="equipment_points")
    op.execute("DELETE FROM equipment_points WHERE length(typequ) > 4")
    op.alter_column("equipment_points", "typequ", type_=sa.String(4), existing_type=sa.String(40), existing_nullable=False)
