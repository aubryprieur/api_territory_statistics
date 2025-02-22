"""modify_schooling_age_sex_to_string

Revision ID: 293e6becbd72
Revises: d297e19f5715
Create Date: 2025-02-21 10:42:28.288794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '293e6becbd72'
down_revision: Union[str, None] = 'd297e19f5715'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Modifier la colonne age de Integer à String en convertissant les valeurs
    op.execute("ALTER TABLE schooling ALTER COLUMN age TYPE VARCHAR(2) USING LPAD(age::text, 2, '0')")

    # Modifier la colonne sex de Integer à String en convertissant les valeurs
    op.execute("ALTER TABLE schooling ALTER COLUMN sex TYPE VARCHAR(1) USING sex::text")

def downgrade() -> None:
    # Revenir à Integer en cas de rollback
    op.execute("ALTER TABLE schooling ALTER COLUMN age TYPE INTEGER USING age::integer")
    op.execute("ALTER TABLE schooling ALTER COLUMN sex TYPE INTEGER USING sex::integer")
