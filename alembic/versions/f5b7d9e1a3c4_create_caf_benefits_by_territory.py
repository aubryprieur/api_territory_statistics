"""create caf_benefits_by_territory (prestations CAF — Cnaf, data.caf.fr)

Revision ID: f5b7d9e1a3c4
Revises: e4a6c8d0f2b3
Create Date: 2026-10-08

Une ligne par (geo_level, geo_code, year), au 31 décembre 2020 à 2024 : pour chaque prestation, foyers
allocataires (<prestation>_households), personnes couvertes (<prestation>_persons) et montant mensuel
versé (<prestation>_amount) ; bénéficiaires de l'AAH et de l'AEEH.
geo_level ∈ COM, ARM, EPCI, DEP (Cnaf), REG et FRANCE ('FM', France métropolitaine) par somme des départements.
Import : scripts/import_caf_benefits_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f5b7d9e1a3c4'
down_revision: Union[str, None] = 'e4a6c8d0f2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MEASURES = ['all_households', 'all_persons', 'all_amount', 'paje_households', 'paje_persons', 'paje_amount', 'paje_basic_households', 'paje_basic_persons', 'paje_basic_amount', 'cmg_households', 'cmg_persons', 'cmg_amount', 'prepare_households', 'prepare_persons', 'prepare_amount', 'children_households', 'children_persons', 'children_amount', 'af_households', 'af_persons', 'af_amount', 'cf_households', 'cf_persons', 'cf_amount', 'ars_households', 'ars_persons', 'ars_amount', 'asf_households', 'asf_persons', 'asf_amount', 'disability_households', 'disability_persons', 'disability_amount', 'aah_households', 'aah_persons', 'aah_amount', 'aeeh_households', 'aeeh_persons', 'aeeh_amount', 'housing_households', 'housing_persons', 'housing_amount', 'apl_households', 'apl_persons', 'apl_amount', 'alf_households', 'alf_persons', 'alf_amount', 'als_households', 'als_persons', 'als_amount', 'insertion_households', 'insertion_persons', 'insertion_amount', 'rsa_households', 'rsa_persons', 'rsa_amount', 'ppa_households', 'ppa_persons', 'ppa_amount', 'aah_beneficiaries', 'aeeh_beneficiaries']


def upgrade() -> None:
    op.create_table(
        'caf_benefits_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(m, sa.Float(), nullable=True) for m in MEASURES],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('caf_benefits_by_territory')
