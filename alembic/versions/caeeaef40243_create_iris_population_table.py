"""create_iris_population_table

Revision ID: caeeaef40243
Revises: fa1df9b31fd9
Create Date: 2026-05-03 09:48:33.050912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caeeaef40243'
down_revision: Union[str, None] = 'fa1df9b31fd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
