"""create_iris_activity_table

Revision ID: 86aa7d48de09
Revises: dc5944508afd
Create Date: 2026-05-03 19:04:33.173022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86aa7d48de09'
down_revision: Union[str, None] = 'dc5944508afd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'iris_activity',
        sa.Column('id',        sa.Integer(),   nullable=False),
        sa.Column('iris_code', sa.String(9),   nullable=False),
        sa.Column('com_code',  sa.String(5),   nullable=False),
        sa.Column('iris_name', sa.String(255), nullable=True),
        sa.Column('dep_code',  sa.String(3),   nullable=True),
        sa.Column('reg_code',  sa.String(2),   nullable=True),
        sa.Column('year',      sa.Integer(),   nullable=False),
        # Population 15-64 ans — Total
        sa.Column('pop_15_64',  sa.Float(), nullable=True),
        sa.Column('pop_15_24',  sa.Float(), nullable=True),
        sa.Column('pop_25_54',  sa.Float(), nullable=True),
        sa.Column('pop_55_64',  sa.Float(), nullable=True),
        # Population 15-64 ans — Hommes
        sa.Column('pop_men_15_64', sa.Float(), nullable=True),
        sa.Column('pop_men_15_24', sa.Float(), nullable=True),
        sa.Column('pop_men_25_54', sa.Float(), nullable=True),
        sa.Column('pop_men_55_64', sa.Float(), nullable=True),
        # Population 15-64 ans — Femmes
        sa.Column('pop_women_15_64', sa.Float(), nullable=True),
        sa.Column('pop_women_15_24', sa.Float(), nullable=True),
        sa.Column('pop_women_25_54', sa.Float(), nullable=True),
        sa.Column('pop_women_55_64', sa.Float(), nullable=True),
        # Actifs — Total
        sa.Column('active_15_64', sa.Float(), nullable=True),
        sa.Column('active_15_24', sa.Float(), nullable=True),
        sa.Column('active_25_54', sa.Float(), nullable=True),
        sa.Column('active_55_64', sa.Float(), nullable=True),
        # Actifs — Hommes
        sa.Column('active_men_15_64', sa.Float(), nullable=True),
        sa.Column('active_men_15_24', sa.Float(), nullable=True),
        sa.Column('active_men_25_54', sa.Float(), nullable=True),
        sa.Column('active_men_55_64', sa.Float(), nullable=True),
        # Actifs — Femmes
        sa.Column('active_women_15_64', sa.Float(), nullable=True),
        sa.Column('active_women_15_24', sa.Float(), nullable=True),
        sa.Column('active_women_25_54', sa.Float(), nullable=True),
        sa.Column('active_women_55_64', sa.Float(), nullable=True),
        # Actifs occupés — Total
        sa.Column('employed_15_64', sa.Float(), nullable=True),
        sa.Column('employed_15_24', sa.Float(), nullable=True),
        sa.Column('employed_25_54', sa.Float(), nullable=True),
        sa.Column('employed_55_64', sa.Float(), nullable=True),
        # Actifs occupés — Hommes
        sa.Column('employed_men_15_64', sa.Float(), nullable=True),
        sa.Column('employed_men_15_24', sa.Float(), nullable=True),
        sa.Column('employed_men_25_54', sa.Float(), nullable=True),
        sa.Column('employed_men_55_64', sa.Float(), nullable=True),
        # Actifs occupés — Femmes
        sa.Column('employed_women_15_64', sa.Float(), nullable=True),
        sa.Column('employed_women_15_24', sa.Float(), nullable=True),
        sa.Column('employed_women_25_54', sa.Float(), nullable=True),
        sa.Column('employed_women_55_64', sa.Float(), nullable=True),
        # Chômeurs par tranche d'âge
        sa.Column('unemp_15_64', sa.Float(), nullable=True),
        sa.Column('unemp_15_24', sa.Float(), nullable=True),
        sa.Column('unemp_25_54', sa.Float(), nullable=True),
        sa.Column('unemp_55_64', sa.Float(), nullable=True),
        # Actifs par diplôme
        sa.Column('active_no_dip',  sa.Float(), nullable=True),
        sa.Column('active_bepc',    sa.Float(), nullable=True),
        sa.Column('active_capbep',  sa.Float(), nullable=True),
        sa.Column('active_bac',     sa.Float(), nullable=True),
        sa.Column('active_sup2',    sa.Float(), nullable=True),
        sa.Column('active_sup34',   sa.Float(), nullable=True),
        sa.Column('active_sup5',    sa.Float(), nullable=True),
        # Chômeurs par diplôme
        sa.Column('unemp_no_dip',   sa.Float(), nullable=True),
        sa.Column('unemp_bepc',     sa.Float(), nullable=True),
        sa.Column('unemp_capbep',   sa.Float(), nullable=True),
        sa.Column('unemp_bac',      sa.Float(), nullable=True),
        sa.Column('unemp_sup2',     sa.Float(), nullable=True),
        sa.Column('unemp_sup34',    sa.Float(), nullable=True),
        sa.Column('unemp_sup5',     sa.Float(), nullable=True),
        # Inactifs
        sa.Column('inactive_15_64',       sa.Float(), nullable=True),
        sa.Column('inactive_men_15_64',   sa.Float(), nullable=True),
        sa.Column('inactive_women_15_64', sa.Float(), nullable=True),
        sa.Column('student_15_64',        sa.Float(), nullable=True),
        sa.Column('student_men_15_64',    sa.Float(), nullable=True),
        sa.Column('student_women_15_64',  sa.Float(), nullable=True),
        sa.Column('retired_15_64',        sa.Float(), nullable=True),
        sa.Column('retired_men_15_64',    sa.Float(), nullable=True),
        sa.Column('retired_women_15_64',  sa.Float(), nullable=True),
        sa.Column('other_inactive_15_64',       sa.Float(), nullable=True),
        sa.Column('other_inactive_men_15_64',   sa.Float(), nullable=True),
        sa.Column('other_inactive_women_15_64', sa.Float(), nullable=True),
        # Actifs occupés par CSP (compl)
        sa.Column('act_farmers',      sa.Float(), nullable=True),
        sa.Column('act_craftsmen',    sa.Float(), nullable=True),
        sa.Column('act_executives',   sa.Float(), nullable=True),
        sa.Column('act_intermediary', sa.Float(), nullable=True),
        sa.Column('act_employees',    sa.Float(), nullable=True),
        sa.Column('act_workers',      sa.Float(), nullable=True),
        sa.Column('emp_farmers',      sa.Float(), nullable=True),
        sa.Column('emp_craftsmen',    sa.Float(), nullable=True),
        sa.Column('emp_executives',   sa.Float(), nullable=True),
        sa.Column('emp_intermediary', sa.Float(), nullable=True),
        sa.Column('emp_employees',    sa.Float(), nullable=True),
        sa.Column('emp_workers',      sa.Float(), nullable=True),
        # Actifs occupés 15+
        sa.Column('employed_15p',       sa.Float(), nullable=True),
        sa.Column('employed_men_15p',   sa.Float(), nullable=True),
        sa.Column('employed_women_15p', sa.Float(), nullable=True),
        # Salariés / Non-salariés
        sa.Column('salaried_15p',       sa.Float(), nullable=True),
        sa.Column('salaried_men_15p',   sa.Float(), nullable=True),
        sa.Column('salaried_women_15p', sa.Float(), nullable=True),
        sa.Column('self_emp_15p',       sa.Float(), nullable=True),
        sa.Column('self_emp_men_15p',   sa.Float(), nullable=True),
        sa.Column('self_emp_women_15p', sa.Float(), nullable=True),
        # Temps partiel
        sa.Column('employed_15p_pt',    sa.Float(), nullable=True),
        sa.Column('salaried_15p_pt',    sa.Float(), nullable=True),
        sa.Column('salaried_men_pt',    sa.Float(), nullable=True),
        sa.Column('salaried_women_pt',  sa.Float(), nullable=True),
        sa.Column('self_emp_15p_pt',    sa.Float(), nullable=True),
        # Type de contrat
        sa.Column('sal_cdi',     sa.Float(), nullable=True),
        sa.Column('sal_cdd',     sa.Float(), nullable=True),
        sa.Column('sal_interim', sa.Float(), nullable=True),
        sa.Column('sal_aided',   sa.Float(), nullable=True),
        sa.Column('sal_appr',    sa.Float(), nullable=True),
        # Non-salariés par type
        sa.Column('self_emp_indep',  sa.Float(), nullable=True),
        sa.Column('self_emp_employ', sa.Float(), nullable=True),
        sa.Column('self_emp_family', sa.Float(), nullable=True),
        # Lieu de travail
        sa.Column('work_same_commune',      sa.Float(), nullable=True),
        sa.Column('work_other_commune',     sa.Float(), nullable=True),
        sa.Column('work_other_dep_same_reg',sa.Float(), nullable=True),
        sa.Column('work_other_reg_metro',   sa.Float(), nullable=True),
        sa.Column('work_other_reg_domtom',  sa.Float(), nullable=True),
        # Mode de transport (compl)
        sa.Column('transport_none',     sa.Float(), nullable=True),
        sa.Column('transport_walk',     sa.Float(), nullable=True),
        sa.Column('transport_bike',     sa.Float(), nullable=True),
        sa.Column('transport_moto',     sa.Float(), nullable=True),
        sa.Column('transport_car',      sa.Float(), nullable=True),
        sa.Column('transport_transit',  sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iris_code', 'year', name='uq_iris_activity_iris_year'),
    )
    op.create_index('ix_iris_activity_iris_year', 'iris_activity', ['iris_code', 'year'])
    op.create_index('ix_iris_activity_com_year',  'iris_activity', ['com_code',  'year'])
    op.create_index('ix_iris_activity_dep_code',  'iris_activity', ['dep_code'])
    op.create_index('ix_iris_activity_reg_code',  'iris_activity', ['reg_code'])
    op.create_index('ix_iris_activity_year',      'iris_activity', ['year'])


def downgrade() -> None:
    op.drop_index('ix_iris_activity_year',      table_name='iris_activity')
    op.drop_index('ix_iris_activity_reg_code',  table_name='iris_activity')
    op.drop_index('ix_iris_activity_dep_code',  table_name='iris_activity')
    op.drop_index('ix_iris_activity_com_year',  table_name='iris_activity')
    op.drop_index('ix_iris_activity_iris_year', table_name='iris_activity')
    op.drop_table('iris_activity')
