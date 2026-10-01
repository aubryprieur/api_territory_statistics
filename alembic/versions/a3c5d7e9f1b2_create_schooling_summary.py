"""create schooling_summary (pré-agrégation de schooling par commune et année)

Revision ID: a3c5d7e9f1b2
Revises: 86aa7d48de09
Create Date: 2026-10-01

Table de synthèse : une ligne par (geo_code, year) avec les 4 sommes utilisées
par SchoolingService. Mêmes filtres et mêmes CASE que les requêtes d'origine
(sexe 1/2, âges 002 à 005, scolarisés = education_status 1 à 5).
À recalculer après chaque import (scripts/import_schooling.py le fait).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c5d7e9f1b2'
down_revision: Union[str, None] = '86aa7d48de09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Idempotent : la table peut avoir été créée à l'avance avec
# scripts/schooling_summary.sql (pour valider les chiffres avant déploiement).
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS schooling_summary (
    geo_code      TEXT    NOT NULL,
    year          INTEGER NOT NULL,
    total_2y      DOUBLE PRECISION NOT NULL DEFAULT 0,
    schooled_2y   DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_3_5y    DOUBLE PRECISION NOT NULL DEFAULT 0,
    schooled_3_5y DOUBLE PRECISION NOT NULL DEFAULT 0,
    PRIMARY KEY (geo_code, year)
);
CREATE INDEX IF NOT EXISTS ix_schooling_summary_year ON schooling_summary (year);
"""

FILL_SQL = """
INSERT INTO schooling_summary (geo_code, year, total_2y, schooled_2y, total_3_5y, schooled_3_5y)
SELECT
    geo_code,
    year,
    SUM(CASE WHEN age = '002' THEN number ELSE 0 END),
    SUM(CASE WHEN age = '002' AND education_status IN ('1','2','3','4','5') THEN number ELSE 0 END),
    SUM(CASE WHEN age IN ('003','004','005') THEN number ELSE 0 END),
    SUM(CASE WHEN age IN ('003','004','005') AND education_status IN ('1','2','3','4','5') THEN number ELSE 0 END)
FROM schooling
WHERE sex IN ('1','2')
  AND age IN ('002','003','004','005')
GROUP BY geo_code, year
"""


def upgrade() -> None:
    op.execute(CREATE_SQL)
    # Remplir seulement si la table est vide (déjà remplie par le script SQL sinon)
    op.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM schooling_summary) THEN {FILL_SQL}; END IF; END $$;")
    op.execute("ANALYZE schooling_summary")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS schooling_summary")
