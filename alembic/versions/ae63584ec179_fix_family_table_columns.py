"""Fix family table columns

Revision ID: ae63584ec179
Revises: dfc6caf19916
Create Date: 2025-02-15 17:25:31.480892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae63584ec179'
down_revision: Union[str, None] = 'dfc6caf19916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Modifie la table families pour corriger les colonnes."""

    conn = op.get_bind()

    # Récupérer la liste des colonnes existantes
    existing_columns = conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='families'")
    ).fetchall()

    existing_columns = [col[0] for col in existing_columns]

    # Liste des colonnes à ajouter
    columns_to_add = [
        ("total_households", sa.Float),
        ("couples_with_children", sa.Float),
        ("single_parent_families", sa.Float),
        ("single_fathers", sa.Float),
        ("single_mothers", sa.Float),
        ("couples_without_children", sa.Float),
        ("children_under_24_three_siblings", sa.Float),
        ("children_under_24_four_or_more_siblings", sa.Float),
    ]

    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            op.add_column('families', sa.Column(column_name, column_type, nullable=True))


def downgrade():
    """Annule les modifications en cas de rollback."""
    op.drop_column('families', 'total_households')
    op.drop_column('families', 'couples_with_children')
    op.drop_column('families', 'single_parent_families')
    op.drop_column('families', 'single_fathers')
    op.drop_column('families', 'single_mothers')
    op.drop_column('families', 'couples_without_children')
    op.drop_column('families', 'children_under_24_three_siblings')
    op.drop_column('families', 'children_under_24_four_or_more_siblings')
