"""create_iris_education_table

Revision ID: dc5944508afd
Revises: e71dd7da69f9
Create Date: 2026-05-03 18:41:54.739949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc5944508afd'
down_revision: Union[str, None] = 'e71dd7da69f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_education',
        sa.Column('id',        sa.Integer(),   nullable=False),
        sa.Column('iris_code', sa.String(9),   nullable=False),
        sa.Column('com_code',  sa.String(5),   nullable=False),
        sa.Column('iris_name', sa.String(255), nullable=True),
        sa.Column('dep_code',  sa.String(3),   nullable=True),
        sa.Column('reg_code',  sa.String(2),   nullable=True),
        sa.Column('year',      sa.Integer(),   nullable=False),
        # Population par tranche d'âge
        sa.Column('pop_2_5',   sa.Float(), nullable=True),
        sa.Column('pop_6_10',  sa.Float(), nullable=True),
        sa.Column('pop_11_14', sa.Float(), nullable=True),
        sa.Column('pop_15_17', sa.Float(), nullable=True),
        sa.Column('pop_18_24', sa.Float(), nullable=True),
        sa.Column('pop_25_29', sa.Float(), nullable=True),
        sa.Column('pop_30p',   sa.Float(), nullable=True),
        # Scolarisés
        sa.Column('scol_2_5',   sa.Float(), nullable=True),
        sa.Column('scol_6_10',  sa.Float(), nullable=True),
        sa.Column('scol_11_14', sa.Float(), nullable=True),
        sa.Column('scol_15_17', sa.Float(), nullable=True),
        sa.Column('scol_18_24', sa.Float(), nullable=True),
        sa.Column('scol_25_29', sa.Float(), nullable=True),
        sa.Column('scol_30p',   sa.Float(), nullable=True),
        # Non scolarisés 15+ — Total
        sa.Column('nscol_15p',         sa.Float(), nullable=True),
        sa.Column('nscol_15p_no_dip',  sa.Float(), nullable=True),
        sa.Column('nscol_15p_bepc',    sa.Float(), nullable=True),
        sa.Column('nscol_15p_capbep',  sa.Float(), nullable=True),
        sa.Column('nscol_15p_bac',     sa.Float(), nullable=True),
        sa.Column('nscol_15p_sup2',    sa.Float(), nullable=True),
        sa.Column('nscol_15p_sup34',   sa.Float(), nullable=True),
        sa.Column('nscol_15p_sup5',    sa.Float(), nullable=True),
        # Non scolarisés 15+ — Hommes
        sa.Column('nscol_15p_men',         sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_no_dip',  sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_bepc',    sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_capbep',  sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_bac',     sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_sup2',    sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_sup34',   sa.Float(), nullable=True),
        sa.Column('nscol_15p_men_sup5',    sa.Float(), nullable=True),
        # Non scolarisés 15+ — Femmes
        sa.Column('nscol_15p_women',         sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_no_dip',  sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_bepc',    sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_capbep',  sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_bac',     sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_sup2',    sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_sup34',   sa.Float(), nullable=True),
        sa.Column('nscol_15p_women_sup5',    sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iris_code', 'year', name='uq_iris_education_iris_year'),
    )
    op.create_index('ix_iris_education_iris_year', 'iris_education', ['iris_code', 'year'])
    op.create_index('ix_iris_education_com_year',  'iris_education', ['com_code',  'year'])
    op.create_index('ix_iris_education_dep_code',  'iris_education', ['dep_code'])
    op.create_index('ix_iris_education_reg_code',  'iris_education', ['reg_code'])
    op.create_index('ix_iris_education_year',      'iris_education', ['year'])


def downgrade() -> None:
    op.drop_index('ix_iris_education_year',      table_name='iris_education')
    op.drop_index('ix_iris_education_reg_code',  table_name='iris_education')
    op.drop_index('ix_iris_education_dep_code',  table_name='iris_education')
    op.drop_index('ix_iris_education_com_year',  table_name='iris_education')
    op.drop_index('ix_iris_education_iris_year', table_name='iris_education')
    op.drop_table('iris_education')
