"""Add indexes to schooling table

Revision ID: 4025588d045e
Revises: 8ddc6e6bd760
Create Date: 2025-02-22 13:46:59.698922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4025588d045e'
down_revision: Union[str, None] = '8ddc6e6bd760'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Ajoute des index pour optimiser les performances"""
    op.create_index('idx_schooling_year', 'schooling', ['year'])
    op.create_index('idx_schooling_geo_code', 'schooling', ['geo_code'])
    op.create_index('idx_schooling_age', 'schooling', ['age'])
    op.create_index('idx_schooling_sex', 'schooling', ['sex'])
    op.create_index('idx_schooling_education_status', 'schooling', ['education_status'])
    print("✅ Indexes added successfully!")


def downgrade():
    """Supprime les index en cas de rollback"""
    op.drop_index('idx_schooling_year', table_name='schooling')
    op.drop_index('idx_schooling_geo_code', table_name='schooling')
    op.drop_index('idx_schooling_age', table_name='schooling')
    op.drop_index('idx_schooling_sex', table_name='schooling')
    op.drop_index('idx_schooling_education_status', table_name='schooling')
    print("⏪ Indexes removed successfully!")
