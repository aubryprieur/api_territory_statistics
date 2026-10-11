"""create health tables (professionnels de santé, complémentaire santé solidaire, affections de longue durée)

Revision ID: e2a4c6e8f0b1
Revises: d1f3a5c7e9b2
Create Date: 2026-10-11

  - health_professionals_by_territory : densité de professionnels de santé libéraux pour 100 000 habitants (ANCT)
  - health_insurance_by_territory : bénéficiaires du régime général et de la complémentaire santé solidaire (Cnam / Insee)
  - ald_by_territory : affections de longue durée, effectifs et taux standardisés par département (Cnam)
Import : scripts/import_health_by_territory.py
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2a4c6e8f0b1'
down_revision: Union[str, None] = 'd1f3a5c7e9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = {
    'health_professionals_by_territory': ['gp_density', 'nurse_density', 'physio_density', 'dentist_density', 'midwife_density', 'psychologist_density', 'pediatrician_density', 'gynecologist_density', 'psychiatrist_density', 'ophthalmologist_density', 'cardiologist_density', 'dermatologist_density', 'gastroenterologist_density', 'pulmonologist_density', 'ent_density', 'radiologist_density'],
    'health_insurance_by_territory': ['insured', 'insured_men', 'insured_women', 'insured_lt18', 'insured_18_24', 'insured_25_49', 'insured_50_59', 'insured_60_74', 'insured_ge75', 'c2s_free', 'c2s_free_lt18', 'c2s_free_18_24', 'c2s_free_25_49', 'c2s_free_50_59', 'c2s_free_ge60', 'c2s_free_men', 'c2s_free_women', 'c2s_paid', 'c2s_paid_lt18', 'c2s_paid_ge60', 'communes'],
    'ald_by_territory': ['stroke_count', 'stroke_rate', 'heart_failure_count', 'heart_failure_rate', 'diabetes_count', 'diabetes_rate', 'coronary_count', 'coronary_rate', 'respiratory_count', 'respiratory_rate', 'alzheimer_count', 'alzheimer_rate', 'parkinson_count', 'parkinson_rate', 'psychiatric_count', 'psychiatric_rate', 'cancer_count', 'cancer_rate'],
}


def upgrade() -> None:
    for table, measures in TABLES.items():
        op.create_table(
            table,
            sa.Column('geo_level', sa.String(10), nullable=False),
            sa.Column('geo_code', sa.String(10), nullable=False),
            sa.Column('year', sa.Integer(), nullable=False),
            *[sa.Column(m, sa.Float(), nullable=True) for m in measures],
            sa.PrimaryKeyConstraint('geo_level', 'geo_code', 'year'),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_table(table)
