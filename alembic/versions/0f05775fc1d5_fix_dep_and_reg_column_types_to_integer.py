"""Fix dep and reg column types to Integer

Revision ID: 0f05775fc1d5
Revises: 7a9104d04564
Create Date: 2025-02-15 16:16:32.450620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f05775fc1d5'
down_revision: Union[str, None] = '7a9104d04564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Modification du type de dep et reg de SmallInteger à Integer
    op.alter_column('geo_codes', 'dep', type_=sa.Integer(), existing_type=sa.Integer())
    op.alter_column('geo_codes', 'reg', type_=sa.Integer(), existing_type=sa.Integer())


def downgrade() -> None:
    # Revenir à SmallInteger en cas de rollback
    op.alter_column('geo_codes', 'dep', type_=sa.SmallInteger(), existing_type=sa.Integer())
    op.alter_column('geo_codes', 'reg', type_=sa.SmallInteger(), existing_type=sa.Integer())
