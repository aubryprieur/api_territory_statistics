-- Crée (si besoin) et (re)calcule la table de synthèse schooling_summary.
-- Une ligne par (geo_code, year) avec les 4 sommes utilisées par SchoolingService.
-- Mêmes filtres et CASE que les requêtes d'origine sur `schooling`.
-- Usage : heroku pg:psql -a api-population-france --file scripts/schooling_summary.sql
-- À relancer après chaque import de données de scolarisation.

BEGIN;

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

TRUNCATE schooling_summary;

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
GROUP BY geo_code, year;

COMMIT;

ANALYZE schooling_summary;

SELECT year, count(*) AS communes, round(sum(total_2y)) AS enfants_2ans, round(sum(total_3_5y)) AS enfants_3_5ans
FROM schooling_summary GROUP BY year ORDER BY year;
