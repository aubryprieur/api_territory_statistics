"""Create geo_codes table

Revision ID: 598c90db37c4
Revises: 
Create Date: 2025-02-22 14:40:05.963448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '598c90db37c4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "geo_codes",
        sa.Column("codgeo", sa.String(10), primary_key=True),
        sa.Column("libgeo", sa.String(), nullable=False),
        sa.Column("epci", sa.String(20), nullable=True),
        sa.Column("libepci", sa.String(), nullable=True),
        sa.Column("dep", sa.String(10), nullable=False),
        sa.Column("reg", sa.String(10), nullable=False),
    )

def downgrade():
    op.drop_table("geo_codes")
