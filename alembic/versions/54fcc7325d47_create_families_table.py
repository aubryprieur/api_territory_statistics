"""Create families table

Revision ID: 54fcc7325d47
Revises: 4665133fb108
Create Date: 2025-02-15 15:34:26.674108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54fcc7325d47'
down_revision: Union[str, None] = '4665133fb108'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Création de la table families
    op.create_table(
        'families',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('geo_code', sa.String(10), nullable=False, index=True),
        sa.Column('year', sa.Integer, nullable=False, index=True),
        sa.Column('total_households', sa.Float, nullable=True),
        sa.Column('single_men', sa.Float, nullable=True),
        sa.Column('single_women', sa.Float, nullable=True),
        sa.Column('couples_with_children', sa.Float, nullable=True),
        sa.Column('single_parent_families', sa.Float, nullable=True),
        sa.Column('single_fathers', sa.Float, nullable=True),
        sa.Column('single_mothers', sa.Float, nullable=True),
        sa.Column('couples_without_children', sa.Float, nullable=True),
        sa.Column('large_families', sa.Float, nullable=True),
        sa.Column('children_under_24_no_sibling', sa.Float, nullable=True),
        sa.Column('children_under_24_one_sibling', sa.Float, nullable=True),
        sa.Column('children_under_24_two_siblings', sa.Float, nullable=True),
        sa.Column('children_under_24_three_siblings', sa.Float, nullable=True),
        sa.Column('children_under_24_four_or_more_siblings', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade() -> None:
    # Suppression de la table families en cas de rollback
    op.drop_table('families')
