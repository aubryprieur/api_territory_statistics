"""create_childcare_table

Revision ID: a8497b1d339c
Revises: bf30546ac142
Create Date: 2025-02-27 12:07:30.677718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8497b1d339c'
down_revision: Union[str, None] = 'bf30546ac142'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée la table childcare pour stocker les données de garde d'enfants"""
    op.create_table('childcare',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),

        # Informations du territoire
        sa.Column('territory_type', sa.String(length=10), nullable=False),
        sa.Column('territory_code', sa.String(length=10), nullable=False),
        sa.Column('territory_name', sa.String(), nullable=True),

        # Année de référence
        sa.Column('year', sa.Integer(), nullable=False),

        # Relations hiérarchiques
        sa.Column('parent_type', sa.String(length=10), nullable=True),
        sa.Column('parent_code', sa.String(length=10), nullable=True),
        sa.Column('parent_name', sa.String(), nullable=True),

        # Zone d'emploi (spécifique à certains fichiers)
        sa.Column('employment_zone_code', sa.String(length=10), nullable=True),
        sa.Column('employment_zone_name', sa.String(), nullable=True),

        # Taux de couverture par type d'accueil
        sa.Column('eaje_psu', sa.Float(), nullable=True),
        sa.Column('eaje_hors_psu', sa.Float(), nullable=True),
        sa.Column('eaje_total', sa.Float(), nullable=True),
        sa.Column('preschool', sa.Float(), nullable=True),
        sa.Column('childminder', sa.Float(), nullable=True),
        sa.Column('home_care', sa.Float(), nullable=True),
        sa.Column('individual_total', sa.Float(), nullable=True),
        sa.Column('global_rate', sa.Float(), nullable=True),

        # Source des données
        sa.Column('data_source', sa.String(length=50), nullable=True),

        # Métadonnées
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # Création des index
    op.create_index(op.f('ix_childcare_territory_type'), 'childcare', ['territory_type'], unique=False)
    op.create_index(op.f('ix_childcare_territory_code'), 'childcare', ['territory_code'], unique=False)
    op.create_index(op.f('ix_childcare_year'), 'childcare', ['year'], unique=False)
    op.create_index('ix_childcare_territory_type_code_year', 'childcare', ['territory_type', 'territory_code', 'year'], unique=False)
    op.create_index('ix_childcare_parent_type_code', 'childcare', ['parent_type', 'parent_code'], unique=False)


def downgrade() -> None:
    """Supprime la table childcare"""
    op.drop_index('ix_childcare_parent_type_code', table_name='childcare')
    op.drop_index('ix_childcare_territory_type_code_year', table_name='childcare')
    op.drop_index(op.f('ix_childcare_year'), table_name='childcare')
    op.drop_index(op.f('ix_childcare_territory_code'), table_name='childcare')
    op.drop_index(op.f('ix_childcare_territory_type'), table_name='childcare')
    op.drop_table('childcare')
