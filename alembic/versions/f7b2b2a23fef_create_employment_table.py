"""create_employment_table

Revision ID: f7b2b2a23fef
Revises: 360ef42a2550
Create Date: 2025-02-23 17:56:51.408601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b2b2a23fef'
down_revision: Union[str, None] = '360ef42a2550'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'employment',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('geo_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        # Population active féminine
        sa.Column('women_15_64', sa.Float, nullable=True),  # Population totale
        sa.Column('women_active_15_64', sa.Float, nullable=True),  # Femmes actives
        sa.Column('women_employed_15_64', sa.Float, nullable=True),  # Femmes ayant un emploi
        # Temps partiel
        sa.Column('women_employees_25_54', sa.Float, nullable=True),  # Total salariées 25-54
        sa.Column('women_part_time_25_54', sa.Float, nullable=True),  # Temps partiel 25-54
        sa.Column('women_employees_15_64', sa.Float, nullable=True),  # Total salariées 15-64
        sa.Column('women_part_time_15_64', sa.Float, nullable=True),  # Temps partiel 15-64
        # Métadonnées
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Indexes
    op.create_index('ix_employment_geo_code', 'employment', ['geo_code'])
    op.create_index('ix_employment_year', 'employment', ['year'])

    # Composite index
    op.create_index('ix_employment_geo_year', 'employment', ['geo_code', 'year'])

def downgrade():
    op.drop_index('ix_employment_geo_year')
    op.drop_index('ix_employment_year')
    op.drop_index('ix_employment_geo_code')
    op.drop_table('employment')
