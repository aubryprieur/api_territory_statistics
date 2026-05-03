"""create_iris_housing_table

Revision ID: e71dd7da69f9
Revises: 6bf7bc21ddf0
Create Date: 2026-05-03 15:35:38.201127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e71dd7da69f9'
down_revision: Union[str, None] = '6bf7bc21ddf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_housing',
        sa.Column('id',        sa.Integer(),     nullable=False),
        sa.Column('iris_code', sa.String(9),     nullable=False),
        sa.Column('com_code',  sa.String(5),     nullable=False),
        sa.Column('iris_name', sa.String(255),   nullable=True),
        sa.Column('dep_code',  sa.String(3),     nullable=True),
        sa.Column('reg_code',  sa.String(2),     nullable=True),
        sa.Column('year',      sa.Integer(),     nullable=False),
        # Logements
        sa.Column('housing_total',       sa.Float(), nullable=True),  # P22_LOG
        sa.Column('main_res',            sa.Float(), nullable=True),  # P22_RP
        sa.Column('second_res',          sa.Float(), nullable=True),  # P22_RSECOCC
        sa.Column('vacant',              sa.Float(), nullable=True),  # P22_LOGVAC
        sa.Column('houses',              sa.Float(), nullable=True),  # P22_MAISON
        sa.Column('apartments',          sa.Float(), nullable=True),  # P22_APPART
        # Résidences principales par nombre de pièces
        sa.Column('rp_1room',            sa.Float(), nullable=True),  # P22_RP_1P
        sa.Column('rp_2rooms',           sa.Float(), nullable=True),  # P22_RP_2P
        sa.Column('rp_3rooms',           sa.Float(), nullable=True),  # P22_RP_3P
        sa.Column('rp_4rooms',           sa.Float(), nullable=True),  # P22_RP_4P
        sa.Column('rp_5p_rooms',         sa.Float(), nullable=True),  # P22_RP_5PP
        # Résidences principales par surface
        sa.Column('rp_u30m2',            sa.Float(), nullable=True),  # P22_RP_M30M2
        sa.Column('rp_30_40m2',          sa.Float(), nullable=True),  # P22_RP_3040M2
        sa.Column('rp_40_60m2',          sa.Float(), nullable=True),  # P22_RP_4060M2
        sa.Column('rp_60_80m2',          sa.Float(), nullable=True),  # P22_RP_6080M2
        sa.Column('rp_80_100m2',         sa.Float(), nullable=True),  # P22_RP_80100M2
        sa.Column('rp_100_120m2',        sa.Float(), nullable=True),  # P22_RP_100120M2
        sa.Column('rp_120p_m2',          sa.Float(), nullable=True),  # P22_RP_120M2P
        # Résidences principales par période de construction
        sa.Column('rp_built_pre1919',    sa.Float(), nullable=True),  # P22_RP_ACH1919
        sa.Column('rp_built_1919_1945',  sa.Float(), nullable=True),  # P22_RP_ACH1945
        sa.Column('rp_built_1946_1970',  sa.Float(), nullable=True),  # P22_RP_ACH1970
        sa.Column('rp_built_1971_1990',  sa.Float(), nullable=True),  # P22_RP_ACH1990
        sa.Column('rp_built_1991_2005',  sa.Float(), nullable=True),  # P22_RP_ACH2005
        sa.Column('rp_built_2006_2019',  sa.Float(), nullable=True),  # P22_RP_ACH2019
        # Ménages
        sa.Column('households',          sa.Float(), nullable=True),  # P22_MEN
        sa.Column('hh_moved_u2y',        sa.Float(), nullable=True),  # P22_MEN_ANEM0002
        sa.Column('hh_moved_2_4y',       sa.Float(), nullable=True),  # P22_MEN_ANEM0204
        sa.Column('hh_moved_5_9y',       sa.Float(), nullable=True),  # P22_MEN_ANEM0509
        sa.Column('hh_moved_10py',       sa.Float(), nullable=True),  # P22_MEN_ANEM10P
        # Statut d'occupation
        sa.Column('rp_owners',           sa.Float(), nullable=True),  # P22_RP_PROP
        sa.Column('rp_renters',          sa.Float(), nullable=True),  # P22_RP_LOC
        sa.Column('rp_social_housing',   sa.Float(), nullable=True),  # P22_RP_LOCHLMV
        sa.Column('rp_free',             sa.Float(), nullable=True),  # P22_RP_GRAT
        # Chauffage
        sa.Column('heat_gas_network',    sa.Float(), nullable=True),  # P22_RP_CGAZV
        sa.Column('heat_fuel',           sa.Float(), nullable=True),  # P22_RP_CFIOUL
        sa.Column('heat_electric',       sa.Float(), nullable=True),  # P22_RP_CELEC
        sa.Column('heat_gas_bottle',     sa.Float(), nullable=True),  # P22_RP_CGAZB
        sa.Column('heat_other',          sa.Float(), nullable=True),  # P22_RP_CAUT
        # Voitures
        sa.Column('hh_1p_car',           sa.Float(), nullable=True),  # P22_RP_VOIT1P
        sa.Column('hh_1_car',            sa.Float(), nullable=True),  # P22_RP_VOIT1
        sa.Column('hh_2p_cars',          sa.Float(), nullable=True),  # P22_RP_VOIT2P
        # Occupation
        sa.Column('rp_standard_occ',     sa.Float(), nullable=True),  # C22_RP_NORME
        sa.Column('rp_mild_underuse',    sa.Float(), nullable=True),  # C22_RP_SOUSOCC_MOD
        sa.Column('rp_heavy_underuse',   sa.Float(), nullable=True),  # C22_RP_SOUSOCC_ACC
        sa.Column('rp_extreme_underuse', sa.Float(), nullable=True),  # C22_RP_SOUSOCC_TACC
        sa.Column('rp_mild_overuse',     sa.Float(), nullable=True),  # C22_RP_SUROCC_MOD
        sa.Column('rp_heavy_overuse',    sa.Float(), nullable=True),  # C22_RP_SUROCC_ACC
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iris_code', 'year', name='uq_iris_housing_iris_year'),
    )
    op.create_index('ix_iris_housing_iris_year', 'iris_housing', ['iris_code', 'year'])
    op.create_index('ix_iris_housing_com_year',  'iris_housing', ['com_code',  'year'])
    op.create_index('ix_iris_housing_dep_code',  'iris_housing', ['dep_code'])
    op.create_index('ix_iris_housing_reg_code',  'iris_housing', ['reg_code'])
    op.create_index('ix_iris_housing_year',      'iris_housing', ['year'])


def downgrade() -> None:
    op.drop_index('ix_iris_housing_year',      table_name='iris_housing')
    op.drop_index('ix_iris_housing_reg_code',  table_name='iris_housing')
    op.drop_index('ix_iris_housing_dep_code',  table_name='iris_housing')
    op.drop_index('ix_iris_housing_com_year',  table_name='iris_housing')
    op.drop_index('ix_iris_housing_iris_year', table_name='iris_housing')
    op.drop_table('iris_housing')
