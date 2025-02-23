"""create_public_safety_table

Revision ID: 360ef42a2550
Revises: 1b4a1e58c917
Create Date: 2025-02-22 16:26:01.066096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '360ef42a2550'
down_revision: Union[str, None] = '1b4a1e58c917'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'public_safety',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('territory_type', sa.String(20), nullable=False),  # 'commune', 'department', 'region'
        sa.Column('territory_code', sa.String(10), nullable=False),
        sa.Column('year', sa.Integer, nullable=False),
        sa.Column('indicator_class', sa.String(50), nullable=False),  # Type d'infraction
        sa.Column('rate', sa.Float, nullable=False),  # Taux pour mille
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Créer des index pour optimiser les requêtes
    op.create_index('ix_public_safety_territory_type', 'public_safety', ['territory_type'])
    op.create_index('ix_public_safety_territory_code', 'public_safety', ['territory_code'])
    op.create_index('ix_public_safety_year', 'public_safety', ['year'])

    # Créer un index composite pour les requêtes courantes
    op.create_index(
        'ix_public_safety_territory_year',
        'public_safety',
        ['territory_type', 'territory_code', 'year']
    )

def downgrade():
    op.drop_index('ix_public_safety_territory_year')
    op.drop_index('ix_public_safety_year')
    op.drop_index('ix_public_safety_territory_code')
    op.drop_index('ix_public_safety_territory_type')
    op.drop_table('public_safety')
