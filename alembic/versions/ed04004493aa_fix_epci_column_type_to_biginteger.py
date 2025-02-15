"""Fix epci column type to BigInteger

Revision ID: ed04004493aa
Revises: 0f05775fc1d5
Create Date: 2025-02-15 16:31:59.290003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed04004493aa'
down_revision: Union[str, None] = '0f05775fc1d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Modifier epci de VARCHAR(20) à BIGINT avec une conversion explicite
    op.execute("ALTER TABLE geo_codes ALTER COLUMN epci TYPE BIGINT USING epci::BIGINT")

def downgrade() -> None:
    # Revenir à VARCHAR(20) en cas de rollback
    op.execute("ALTER TABLE geo_codes ALTER COLUMN epci TYPE VARCHAR(20) USING epci::VARCHAR")
