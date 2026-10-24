"""create grid_filosofi_1km (Insee, Filosofi 2021, carreaux de 1 km, France métropolitaine)

Revision ID: a8c0e2f4b6d8
Revises: f7b9d1e3a5c6
Create Date: 2026-10-24

Une ligne par carreau habité (identifiant Insee CRS3035RES1000mN{y}E{x}) : coin inférieur gauche en LAEA (x, y),
indicateur d'imputation, communes touchées (tableau, index GIN), et les effectifs utiles aux cartes (individus,
ménages, ménages pauvres, monoparentaux, en logement social, somme des niveaux de vie, 0-3 ans, 80 ans ou plus).
Pas de géométrie stockée : les coins sont calculés à la demande (app/utils/laea.py).
Import : scripts/import_grid_filosofi.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a8c0e2f4b6d8'
down_revision: Union[str, None] = 'f7b9d1e3a5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['ind', 'men', 'men_pauv', 'men_fmp', 'log_soc', 'ind_snv', 'ind_0_3', 'ind_80p']


def upgrade() -> None:
    op.create_table(
        'grid_filosofi_1km',
        sa.Column('idcar', sa.String(40), primary_key=True),
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('imputed', sa.SmallInteger(), nullable=True),
        sa.Column('communes', postgresql.ARRAY(sa.String(5)), nullable=False),
        *[sa.Column(m, sa.REAL(), nullable=True) for m in MEASURES],
    )
    op.create_index('ix_grid_filosofi_1km_communes', 'grid_filosofi_1km', ['communes'], postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_grid_filosofi_1km_communes', table_name='grid_filosofi_1km')
    op.drop_table('grid_filosofi_1km')
