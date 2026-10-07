"""create households_by_territory (ménages RP INSEE, toutes échelles)

Revision ID: c5e7a9b1d3f4
Revises: b4d6f8a0c2e3
Create Date: 2026-10-07

Une ligne par (geo_level, geo_code, year), alimentée directement par les fichiers INSEE
DS_RP_MENAGES_COMP (ménages par type et par PCS de la personne de référence) et
DS_RP_MENAGES_PRINC (personnes vivant seules par âge). Valeurs officielles, sans agrégation.
geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine).
Millésimes : 2012, 2017, 2023. Import : scripts/import_households_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5e7a9b1d3f4'
down_revision: Union[str, None] = 'b4d6f8a0c2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AGES = ["15_24", "25_39", "40_54", "55_64", "65_79", "80_plus"]
MEASURES = (
    [
        "households",                      # nombre de ménages (= résidences principales)
        "household_population",            # population des ménages
        "one_person",                      # ménages d'une personne
        "men_alone",
        "women_alone",
        "other_without_family",            # ménages sans famille de plusieurs personnes
        "with_family",                     # ménages avec famille(s)
        "single_parent",                   # famille principale monoparentale
        "couple_without_children",
        "couple_with_children",
    ]
    + [f"pcs_{c}" for c in ["1", "2", "3", "4", "5", "6", "7", "9"]]  # ménages selon la PCS de la personne de référence
    + [f"living_alone_{a}" for a in AGES]                              # personnes vivant seules, par âge
    + [f"household_population_{a}" for a in AGES]                      # population des ménages, par âge
)


def upgrade() -> None:
    op.create_table(
        'households_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('households_by_territory')
