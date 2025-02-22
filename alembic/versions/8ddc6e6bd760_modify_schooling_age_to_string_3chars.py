"""modify_schooling_age_to_string_3chars

Revision ID: 8ddc6e6bd760
Revises: 293e6becbd72
Create Date: 2025-02-21 12:30:11.451965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ddc6e6bd760'
down_revision: Union[str, None] = '293e6becbd72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Modifier la colonne age pour qu'elle accepte 3 caractères
    op.execute("ALTER TABLE schooling ALTER COLUMN age TYPE VARCHAR(3) USING LPAD(age::text, 3, '0')")

def downgrade() -> None:
    # Revenir à VARCHAR(2) en cas de rollback (perdra les valeurs "003" -> "00")
    op.execute("ALTER TABLE schooling ALTER COLUMN age TYPE VARCHAR(2) USING LPAD(age::text, 2, '0')")
