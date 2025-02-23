"""Create births table

Revision ID: da837d56ac27
Revises: 3a70fd755c35
Create Date: 2025-02-22 14:40:15.959688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da837d56ac27'
down_revision: Union[str, None] = '3a70fd755c35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "births",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("geo", sa.String(), nullable=False),
        sa.Column("geo_object", sa.String(), nullable=False),
        sa.Column("time_period", sa.Integer(), nullable=False),
        sa.Column("obs_value", sa.Float(), nullable=False),
    )

def downgrade():
    op.drop_table("births")
