-- Audit des valeurs NaN dans toutes les colonnes Float (une ligne par table)
-- Usage : heroku pg:psql -a api-population-france --file scripts/audit_nan.sql
SELECT 'births' AS table_name, count(*) AS lignes_nan FROM births WHERE obs_value = 'NaN'
UNION ALL
SELECT 'families' AS table_name, count(*) AS lignes_nan FROM families WHERE total_households = 'NaN' OR single_men = 'NaN' OR single_women = 'NaN' OR couples_with_children = 'NaN' OR single_parent_families = 'NaN' OR single_fathers = 'NaN' OR single_mothers = 'NaN' OR couples_without_children = 'NaN' OR large_families = 'NaN' OR children_under_24_no_sibling = 'NaN' OR children_under_24_one_sibling = 'NaN' OR children_under_24_two_siblings = 'NaN' OR children_under_24_three_siblings = 'NaN' OR children_under_24_four_or_more_siblings = 'NaN'
UNION ALL
SELECT 'schooling' AS table_name, count(*) AS lignes_nan FROM schooling WHERE number = 'NaN'
UNION ALL
SELECT 'public_safety' AS table_name, count(*) AS lignes_nan FROM public_safety WHERE rate = 'NaN'
UNION ALL
SELECT 'employment' AS table_name, count(*) AS lignes_nan FROM employment WHERE women_15_64 = 'NaN' OR women_active_15_64 = 'NaN' OR women_employed_15_64 = 'NaN' OR women_employees_25_54 = 'NaN' OR women_part_time_25_54 = 'NaN' OR women_employees_15_64 = 'NaN' OR women_part_time_15_64 = 'NaN'
UNION ALL
SELECT 'historical' AS table_name, count(*) AS lignes_nan FROM historical WHERE pop_1968 = 'NaN' OR pop_1975 = 'NaN' OR pop_1982 = 'NaN' OR pop_1990 = 'NaN' OR pop_1999 = 'NaN' OR pop_2010 = 'NaN' OR pop_2015 = 'NaN' OR pop_2021 = 'NaN'
UNION ALL
SELECT 'revenues' AS table_name, count(*) AS lignes_nan FROM revenues WHERE median_revenue = 'NaN' OR poverty_rate = 'NaN'
UNION ALL
SELECT 'populations' AS table_name, count(*) AS lignes_nan FROM populations WHERE nb = 'NaN'
UNION ALL
SELECT 'family_employment' AS table_name, count(*) AS lignes_nan FROM family_employment WHERE number = 'NaN'
UNION ALL
SELECT 'childcare' AS table_name, count(*) AS lignes_nan FROM childcare WHERE eaje_psu = 'NaN' OR eaje_hors_psu = 'NaN' OR eaje_total = 'NaN' OR preschool = 'NaN' OR childminder = 'NaN' OR home_care = 'NaN' OR individual_total = 'NaN' OR global_rate = 'NaN'
UNION ALL
SELECT 'iris_population' AS table_name, count(*) AS lignes_nan FROM iris_population WHERE pop_immigrant = 'NaN' OR pop_women = 'NaN'
UNION ALL
SELECT 'iris_families' AS table_name, count(*) AS lignes_nan FROM iris_families WHERE pop_15_24_alone = 'NaN' OR pop_25_54_alone = 'NaN' OR pop_55_79_alone = 'NaN' OR couples_with_children = 'NaN' OR families_4p_children = 'NaN'
UNION ALL
SELECT 'iris_housing' AS table_name, count(*) AS lignes_nan FROM iris_housing WHERE rp_extreme_underuse = 'NaN'
UNION ALL
SELECT 'iris_education' AS table_name, count(*) AS lignes_nan FROM iris_education WHERE pop_11_14 = 'NaN' OR pop_15_17 = 'NaN' OR pop_18_24 = 'NaN' OR pop_25_29 = 'NaN' OR scol_11_14 = 'NaN' OR scol_15_17 = 'NaN' OR scol_18_24 = 'NaN' OR scol_25_29 = 'NaN'
UNION ALL
SELECT 'iris_activity' AS table_name, count(*) AS lignes_nan FROM iris_activity WHERE pop_men_15_64 = 'NaN' OR pop_men_15_24 = 'NaN' OR pop_men_25_54 = 'NaN' OR pop_men_55_64 = 'NaN' OR pop_women_15_64 = 'NaN' OR pop_women_15_24 = 'NaN' OR pop_women_25_54 = 'NaN' OR pop_women_55_64 = 'NaN' OR active_15_64 = 'NaN' OR active_15_24 = 'NaN' OR active_25_54 = 'NaN' OR active_55_64 = 'NaN' OR active_men_15_64 = 'NaN' OR active_men_15_24 = 'NaN' OR active_men_25_54 = 'NaN' OR active_men_55_64 = 'NaN' OR active_women_15_64 = 'NaN' OR active_women_15_24 = 'NaN' OR active_women_25_54 = 'NaN' OR active_women_55_64 = 'NaN' OR employed_15_64 = 'NaN' OR employed_15_24 = 'NaN' OR employed_25_54 = 'NaN' OR employed_55_64 = 'NaN' OR employed_men_15_64 = 'NaN' OR employed_men_15_24 = 'NaN' OR employed_men_25_54 = 'NaN' OR employed_men_55_64 = 'NaN' OR employed_women_15_64 = 'NaN' OR employed_women_15_24 = 'NaN' OR employed_women_25_54 = 'NaN' OR employed_women_55_64 = 'NaN' OR unemp_15_64 = 'NaN' OR unemp_15_24 = 'NaN' OR unemp_25_54 = 'NaN' OR unemp_55_64 = 'NaN' OR active_no_dip = 'NaN' OR active_capbep = 'NaN' OR inactive_women_15_64 = 'NaN' OR other_inactive_women_15_64 = 'NaN' OR act_intermediary = 'NaN' OR emp_intermediary = 'NaN' OR employed_women_15p = 'NaN' OR salaried_women_15p = 'NaN' OR self_emp_women_15p = 'NaN' OR salaried_women_pt = 'NaN' OR sal_interim = 'NaN' OR self_emp_employ = 'NaN' OR self_emp_family = 'NaN' OR work_other_dep_same_reg = 'NaN' OR transport_transit = 'NaN' ORDER BY lignes_nan DESC;
