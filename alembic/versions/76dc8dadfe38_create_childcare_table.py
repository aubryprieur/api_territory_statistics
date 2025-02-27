"""create_childcare_table

Revision ID: 76dc8dadfe38
Revises: a8497b1d339c
Create Date: 2025-02-27 13:36:11.543702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76dc8dadfe38'
down_revision: Union[str, None] = 'a8497b1d339c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
