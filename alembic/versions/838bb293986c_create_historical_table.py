"""create_historical_table

Revision ID: 838bb293986c
Revises: f7b2b2a23fef
Create Date: 2025-02-24 15:01:02.798569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '838bb293986c'
down_revision: Union[str, None] = 'f7b2b2a23fef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'historical',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('codgeo', sa.String(10), nullable=False),
        # Recensements
        sa.Column('pop_1968', sa.Float, nullable=True),
        sa.Column('pop_1975', sa.Float, nullable=True),
        sa.Column('pop_1982', sa.Float, nullable=True),
        sa.Column('pop_1990', sa.Float, nullable=True),
        sa.Column('pop_1999', sa.Float, nullable=True),
        sa.Column('pop_2010', sa.Float, nullable=True),
        sa.Column('pop_2015', sa.Float, nullable=True),
        sa.Column('pop_2021', sa.Float, nullable=True),
        # Métadonnées
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Indexes
    op.create_index('ix_historical_codgeo', 'historical', ['codgeo'])

def downgrade():
    op.drop_index('ix_historical_codgeo')
    op.drop_table('historical')
