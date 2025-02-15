"""
Create geo_codes table

Revision ID: e498a1ed5843
Revises: 54fcc7325d47
Create Date: 2025-02-15 16:02:49.721622

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Identifiants de la migration
revision: str = 'e498a1ed5843'
down_revision: Union[str, None] = '54fcc7325d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'geo_codes',
        sa.Column('codgeo', sa.String(10), nullable=False),  # Correction pour éviter erreurs de type
        sa.Column('libgeo', sa.String(), nullable=False),
        sa.Column('epci', sa.BigInteger(), nullable=True),  # Correction ici pour éviter "integer out of range"
        sa.Column('libepci', sa.String(), nullable=True),
        sa.Column('dep', sa.SmallInteger(), nullable=False),  # SmallInteger car max 976
        sa.Column('reg', sa.SmallInteger(), nullable=False),  # SmallInteger car max 100
        sa.PrimaryKeyConstraint('codgeo')
    )
    op.create_index(op.f('ix_geo_codes_codgeo'), 'geo_codes', ['codgeo'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_geo_codes_codgeo'), table_name='geo_codes')
    op.drop_table('geo_codes')
