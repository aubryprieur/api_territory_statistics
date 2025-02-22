"""Create partitioned schooling table

Revision ID: 1b4a1e58c917
Revises: da837d56ac27
Create Date: 2025-02-22 14:40:20.557803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b4a1e58c917'
down_revision: Union[str, None] = 'da837d56ac27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Création de la table mère partitionnée
    op.execute("""
        CREATE TABLE schooling (
            id SERIAL,
            geo_code TEXT NOT NULL,
            year INT NOT NULL,
            age TEXT NOT NULL,
            sex TEXT NOT NULL,
            education_status TEXT NOT NULL,
            number FLOAT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (year, id)  -- Ajout de year dans la clé primaire
        ) PARTITION BY LIST (year);
    """)

    # Création des partitions pour les années 2017-2021
    for year in range(2017, 2022):
        op.execute(f"""
            CREATE TABLE schooling_{year} PARTITION OF schooling
            FOR VALUES IN ({year});
        """)

def downgrade():
    for year in range(2017, 2022):
        op.execute(f"DROP TABLE IF EXISTS schooling_{year} CASCADE;")
    op.execute("DROP TABLE IF EXISTS schooling CASCADE;")
