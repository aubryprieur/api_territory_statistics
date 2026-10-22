"""create fragility_synthesis + fragility_reference (synthèse des fragilités)

Revision ID: f7b9d1e3a5c6
Revises: e6a8c0d2f4b5
Create Date: 2026-10-22

fragility_synthesis : une ligne par commune — catégorie de densité INSEE (7 niveaux), population, et en JSONB pour
chaque indicateur du catalogue (app/fragility_catalog.py) : valeur, effectif, rang national et rang dans la catégorie
de densité (0 = moins touchée, 100 = plus touchée).
fragility_reference : par indicateur et par périmètre (FR ou code de densité) : millésime, nombre de communes, médiane,
seuil des 20 % les plus touchées, valeur France.
Import : scripts/import_fragility_synthesis.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f7b9d1e3a5c6'
down_revision: Union[str, None] = 'e6a8c0d2f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fragility_synthesis',
        sa.Column('geo_code', sa.String(10), primary_key=True),
        sa.Column('dens7', sa.String(2), nullable=True),
        sa.Column('dens7_label', sa.String(60), nullable=True),
        sa.Column('population', sa.Float(), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        'fragility_reference',
        sa.Column('indicator', sa.String(40), nullable=False),
        sa.Column('scope', sa.String(4), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('n', sa.Integer(), nullable=True),
        sa.Column('median', sa.Float(), nullable=True),
        sa.Column('alert_value', sa.Float(), nullable=True),
        sa.Column('france_value', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('indicator', 'scope'),
    )


def downgrade() -> None:
    op.drop_table('fragility_reference')
    op.drop_table('fragility_synthesis')
