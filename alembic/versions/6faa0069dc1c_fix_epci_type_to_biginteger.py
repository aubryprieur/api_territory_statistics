"""Fix EPCI type to BigInteger

Revision ID: 6faa0069dc1c
Revises: e498a1ed5843
Create Date: 2025-02-15 16:09:14.698230

"""
from alembic import op
import sqlalchemy as sa

# Identifiants de la migration
revision = '6faa0069dc1c'
down_revision = 'e498a1ed5843'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Modification du type de la colonne epci
    op.alter_column(
        'geo_codes',
        'epci',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True
    )

def downgrade() -> None:
    # Revenir à Integer en cas de rollback
    op.alter_column(
        'geo_codes',
        'epci',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True
    )
