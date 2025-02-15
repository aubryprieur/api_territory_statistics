"""Fix geocode column types to VARCHAR

Revision ID: dfc6caf19916
Revises: ed04004493aa
Create Date: 2025-02-15 16:45:13.353962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfc6caf19916'
down_revision: Union[str, None] = 'ed04004493aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('geo_codes', 'epci', existing_type=sa.BigInteger(), type_=sa.String(20))
    op.alter_column('geo_codes', 'dep', existing_type=sa.Integer(), type_=sa.String(5))
    op.alter_column('geo_codes', 'reg', existing_type=sa.Integer(), type_=sa.String(5))

def downgrade():
    op.alter_column('geo_codes', 'epci', existing_type=sa.String(20), type_=sa.BigInteger())
    op.alter_column('geo_codes', 'dep', existing_type=sa.String(5), type_=sa.Integer())
    op.alter_column('geo_codes', 'reg', existing_type=sa.String(5), type_=sa.Integer())
