"""create economic_fabric_by_territory (tissu économique local — INSEE, Flores 2017 et 2021)

Revision ID: d9f1b3c5e7a8
Revises: c8e0a2b4d6f7
Create Date: 2026-10-08

Établissements actifs et postes salariés au 31 décembre par grand secteur, taille, sphère présentielle / productive,
particuliers employeurs. geo_level ∈ COM, ARM, EPCI, DEP, REG, FRANCE ('FM') ; EPCI, DEP, REG, FM = somme des
communes. Import : scripts/import_economic_fabric_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9f1b3c5e7a8'
down_revision: Union[str, None] = 'c8e0a2b4d6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['ets_total', 'posts_total', 'ets_agriculture', 'posts_agriculture', 'ets_industry', 'posts_industry', 'ets_construction', 'posts_construction', 'ets_market_services', 'posts_market_services', 'ets_trade', 'posts_trade', 'ets_non_market', 'posts_non_market', 'ets_size_0', 'ets_size_1_9', 'ets_size_10_19', 'ets_size_20_49', 'ets_size_50p', 'posts_size_1_9', 'posts_size_10_19', 'posts_size_20_49', 'posts_size_50_99', 'posts_size_100p', 'ets_presential', 'ets_productive', 'ets_presential_public', 'ets_productive_public', 'posts_presential', 'posts_productive', 'posts_presential_public', 'posts_productive_public', 'childminder_employers', 'other_home_employers']


def upgrade() -> None:
    op.create_table(
        'economic_fabric_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('economic_fabric_by_territory')
