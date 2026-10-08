"""create schools_by_year, schools_national_by_year, sixth_grade_age_by_territory (Éducation nationale)

Revision ID: b7d9f1a3c5e6
Revises: a6c8e0f2b4d5
Create Date: 2026-10-08

Indicateurs des établissements scolaires (IPS, valeurs ajoutées, indice d'éloignement) par (uai, year),
distribution nationale par type d'établissement, âge à l'entrée en 6e par département, région, France.
Import : scripts/import_schools.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7d9f1a3c5e6'
down_revision: Union[str, None] = 'a6c8e0f2b4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEXT = {'school_type': 10, 'lycee_type': 10, 'name': None, 'sector': 10, 'commune_code': 5,
        'commune_name': None, 'department_code': 3}
INTEGER = ['ips_decile', 'remoteness_decile']
FLOAT = ['ips', 'ips_sd', 'ips_gt', 'ips_pro', 'ips_post_bac', 'ips_percentile', 'ips_national',
         'ips_national_public', 'ips_national_private', 'ips_academic', 'ips_departmental',
         'ips_departmental_public', 'ips_departmental_private', 'remoteness', 'remoteness_percentile',
         'dnb_candidates', 'dnb_success_rate', 'dnb_success_va', 'dnb_written_score', 'dnb_written_va',
         'dnb_mentions_rate', 'dnb_tb_rate', 'access_6_3_rate', 'dnb_success_va_percentile',
         'dnb_written_va_percentile',
         'gt_candidates', 'gt_success_rate', 'gt_success_va', 'gt_access_rate', 'gt_access_va', 'gt_mentions_rate',
         'gt_mentions_va', 'gt_success_va_percentile', 'gt_access_va_percentile',
         'pro_candidates', 'pro_success_rate', 'pro_success_va', 'pro_access_rate', 'pro_access_va',
         'pro_mentions_rate', 'pro_mentions_va', 'pro_success_va_percentile', 'pro_access_va_percentile']
SIXTH = [f"{m}_{g}" for g in ("total", "girls", "boys", "public", "private")
         for m in ("pupils", "on_time", "early", "late")]


def upgrade() -> None:
    op.create_table(
        'schools_by_year',
        sa.Column('uai', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(c, sa.String(n) if n else sa.String(), nullable=True) for c, n in TEXT.items()],
        *[sa.Column(c, sa.Integer(), nullable=True) for c in INTEGER],
        *[sa.Column(c, sa.Float(), nullable=True) for c in FLOAT],
        sa.PrimaryKeyConstraint('uai', 'year'),
    )
    op.create_index('ix_schools_by_year_commune_code', 'schools_by_year', ['commune_code'])
    op.create_table(
        'schools_national_by_year',
        sa.Column('school_type', sa.String(20), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('metric', sa.String(40), nullable=False),
        sa.Column('establishments', sa.Integer(), nullable=True),
        sa.Column('mean', sa.Float(), nullable=True),
        *[sa.Column(f'd{i}', sa.Float(), nullable=True) for i in range(1, 10)],
        sa.PrimaryKeyConstraint('school_type', 'year', 'metric'),
    )
    op.create_table(
        'sixth_grade_age_by_territory',
        sa.Column('geo_level', sa.String(10), nullable=False),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        *[sa.Column(c, sa.Float(), nullable=True) for c in SIXTH],
        sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
    )


def downgrade() -> None:
    op.drop_table('sixth_grade_age_by_territory')
    op.drop_table('schools_national_by_year')
    op.drop_index('ix_schools_by_year_commune_code', table_name='schools_by_year')
    op.drop_table('schools_by_year')
