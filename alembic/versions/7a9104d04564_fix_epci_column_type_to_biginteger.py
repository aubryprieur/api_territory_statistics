"""Fix epci column type to BigInteger

Revision ID: 7a9104d04564
Revises: 6faa0069dc1c
Create Date: 2025-02-15 16:14:35.198529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a9104d04564'
down_revision: Union[str, None] = '6faa0069dc1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
