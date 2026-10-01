-- Compare les résultats de l'ancienne méthode (table schooling) et de la nouvelle (schooling_summary)
-- pour une commune, un EPCI, un département, une région et la France, années 2017-2021.
-- Usage : heroku pg:psql -a api-population-france --file scripts/compare_schooling_summary.sql
-- Attendu : taux identiques (avant = après) et ecart_max ≈ 0.

WITH avant AS (
SELECT '1_commune_59484' AS niveau, s.year,
  SUM(CASE WHEN s.age = '002' THEN s.number ELSE 0 END) AS t2,
  SUM(CASE WHEN s.age = '002' AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s2,
  SUM(CASE WHEN s.age IN ('003','004','005') THEN s.number ELSE 0 END) AS t35,
  SUM(CASE WHEN s.age IN ('003','004','005') AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s35
FROM schooling s 
WHERE s.year BETWEEN 2017 AND 2021 AND s.sex IN ('1','2') AND s.age IN ('002','003','004','005') AND s.geo_code = '59484'
GROUP BY s.year
UNION ALL
SELECT '2_epci_245901160' AS niveau, s.year,
  SUM(CASE WHEN s.age = '002' THEN s.number ELSE 0 END) AS t2,
  SUM(CASE WHEN s.age = '002' AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s2,
  SUM(CASE WHEN s.age IN ('003','004','005') THEN s.number ELSE 0 END) AS t35,
  SUM(CASE WHEN s.age IN ('003','004','005') AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s35
FROM schooling s 
WHERE s.year BETWEEN 2017 AND 2021 AND s.sex IN ('1','2') AND s.age IN ('002','003','004','005') AND s.geo_code IN (SELECT codgeo FROM geo_codes WHERE epci = '245901160')
GROUP BY s.year
UNION ALL
SELECT '3_dep_59' AS niveau, s.year,
  SUM(CASE WHEN s.age = '002' THEN s.number ELSE 0 END) AS t2,
  SUM(CASE WHEN s.age = '002' AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s2,
  SUM(CASE WHEN s.age IN ('003','004','005') THEN s.number ELSE 0 END) AS t35,
  SUM(CASE WHEN s.age IN ('003','004','005') AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s35
FROM schooling s JOIN geo_codes g ON g.codgeo = s.geo_code
WHERE s.year BETWEEN 2017 AND 2021 AND s.sex IN ('1','2') AND s.age IN ('002','003','004','005') AND g.dep = '59'
GROUP BY s.year
UNION ALL
SELECT '4_reg_32' AS niveau, s.year,
  SUM(CASE WHEN s.age = '002' THEN s.number ELSE 0 END) AS t2,
  SUM(CASE WHEN s.age = '002' AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s2,
  SUM(CASE WHEN s.age IN ('003','004','005') THEN s.number ELSE 0 END) AS t35,
  SUM(CASE WHEN s.age IN ('003','004','005') AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s35
FROM schooling s JOIN geo_codes g ON g.codgeo = s.geo_code
WHERE s.year BETWEEN 2017 AND 2021 AND s.sex IN ('1','2') AND s.age IN ('002','003','004','005') AND g.reg = '32'
GROUP BY s.year
UNION ALL
SELECT '5_france' AS niveau, s.year,
  SUM(CASE WHEN s.age = '002' THEN s.number ELSE 0 END) AS t2,
  SUM(CASE WHEN s.age = '002' AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s2,
  SUM(CASE WHEN s.age IN ('003','004','005') THEN s.number ELSE 0 END) AS t35,
  SUM(CASE WHEN s.age IN ('003','004','005') AND s.education_status IN ('1','2','3','4','5') THEN s.number ELSE 0 END) AS s35
FROM schooling s 
WHERE s.year BETWEEN 2017 AND 2021 AND s.sex IN ('1','2') AND s.age IN ('002','003','004','005') AND TRUE
GROUP BY s.year
), apres AS (
SELECT '1_commune_59484' AS niveau, s.year,
  SUM(s.total_2y) AS t2, SUM(s.schooled_2y) AS s2, SUM(s.total_3_5y) AS t35, SUM(s.schooled_3_5y) AS s35
FROM schooling_summary s 
WHERE s.year BETWEEN 2017 AND 2021 AND s.geo_code = '59484'
GROUP BY s.year
UNION ALL
SELECT '2_epci_245901160' AS niveau, s.year,
  SUM(s.total_2y) AS t2, SUM(s.schooled_2y) AS s2, SUM(s.total_3_5y) AS t35, SUM(s.schooled_3_5y) AS s35
FROM schooling_summary s 
WHERE s.year BETWEEN 2017 AND 2021 AND s.geo_code IN (SELECT codgeo FROM geo_codes WHERE epci = '245901160')
GROUP BY s.year
UNION ALL
SELECT '3_dep_59' AS niveau, s.year,
  SUM(s.total_2y) AS t2, SUM(s.schooled_2y) AS s2, SUM(s.total_3_5y) AS t35, SUM(s.schooled_3_5y) AS s35
FROM schooling_summary s JOIN geo_codes g ON g.codgeo = s.geo_code
WHERE s.year BETWEEN 2017 AND 2021 AND g.dep = '59'
GROUP BY s.year
UNION ALL
SELECT '4_reg_32' AS niveau, s.year,
  SUM(s.total_2y) AS t2, SUM(s.schooled_2y) AS s2, SUM(s.total_3_5y) AS t35, SUM(s.schooled_3_5y) AS s35
FROM schooling_summary s JOIN geo_codes g ON g.codgeo = s.geo_code
WHERE s.year BETWEEN 2017 AND 2021 AND g.reg = '32'
GROUP BY s.year
UNION ALL
SELECT '5_france' AS niveau, s.year,
  SUM(s.total_2y) AS t2, SUM(s.schooled_2y) AS s2, SUM(s.total_3_5y) AS t35, SUM(s.schooled_3_5y) AS s35
FROM schooling_summary s 
WHERE s.year BETWEEN 2017 AND 2021 AND TRUE
GROUP BY s.year
)
SELECT a.niveau, a.year,
  round((a.s2 / NULLIF(a.t2, 0) * 100)::numeric, 1)   AS taux_2ans_avant,
  round((b.s2 / NULLIF(b.t2, 0) * 100)::numeric, 1)   AS taux_2ans_apres,
  round((a.s35 / NULLIF(a.t35, 0) * 100)::numeric, 1) AS taux_3_5ans_avant,
  round((b.s35 / NULLIF(b.t35, 0) * 100)::numeric, 1) AS taux_3_5ans_apres,
  GREATEST(abs(a.t2 - b.t2), abs(a.s2 - b.s2), abs(a.t35 - b.t35), abs(a.s35 - b.s35)) AS ecart_max
FROM avant a
LEFT JOIN apres b ON b.niveau = a.niveau AND b.year = a.year
ORDER BY a.niveau, a.year;
