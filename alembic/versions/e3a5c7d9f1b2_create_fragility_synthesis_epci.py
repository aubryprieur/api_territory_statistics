"""create fragility_synthesis_epci (synthèse des fragilités à l'échelle des EPCI)

Revision ID: e3a5c7d9f1b2
Revises: d2f4b6c8e0a1
Create Date: 2026-11-06

Une ligne par EPCI : nature (CC, CA, ME = communautés urbaines et métropoles), population et en JSONB pour chaque
indicateur du catalogue : valeur, effectif, rang parmi tous les EPCI et rang parmi les EPCI de même nature
(0 = moins touché, 100 = plus touché). Repères dans fragility_reference, périmètres EFR (tous les EPCI) et E + nature.
Import : scripts/import_fragility_synthesis.py (calcule communes et EPCI).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e3a5c7d9f1b2'
down_revision: Union[str, None] = 'd2f4b6c8e0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fragility_synthesis_epci',
        sa.Column('geo_code', sa.String(10), primary_key=True),
        sa.Column('nature', sa.String(4), nullable=True),
        sa.Column('nature_label', sa.String(60), nullable=True),
        sa.Column('population', sa.Float(), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('fragility_synthesis_epci')
