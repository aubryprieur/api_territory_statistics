"""
Cartes IRIS : contours (iris_geometries) et indicateurs par IRIS pour une commune, aux millésimes disponibles
(2017, 2022, 2023 ; la carte compare le premier et le dernier), avec la valeur de la commune calculée sur la somme de ses IRIS (même source, même millésime).

Chaque indicateur est un rapport numérateur / dénominateur sur une table iris_* (colonnes additives) : la valeur
communale est donc la somme des numérateurs sur la somme des dénominateurs, ce qui rend l'écart IRIS / commune
cohérent. Les effectifs (numérateur, dénominateur) sont renvoyés pour chaque IRIS.
"""
import json
import logging
from typing import Optional

from sqlalchemy import text

from app.database import SessionLocal

logger = logging.getLogger(__name__)

# clé : (table, [colonnes du numérateur], [colonnes du dénominateur], libellé, libellé de l'effectif, unité)
INDICATORS = {
    "under_18_share": ("iris_population", ["pop_0_2", "pop_3_5", "pop_6_10", "pop_11_17"], ["pop"],
                       "Part des moins de 18 ans", "moins de 18 ans", "%"),
    "age_65p_share": ("iris_population", ["pop_65_79", "pop_80_plus"], ["pop"],
                      "Part des 65 ans ou plus", "personnes de 65 ans ou plus", "%"),
    "age_80p_share": ("iris_population", ["pop_80_plus"], ["pop"],
                      "Part des 80 ans ou plus", "personnes de 80 ans ou plus", "%"),
    "immigrant_share": ("iris_population", ["pop_immigrant"], ["pop"],
                        "Part des immigrés", "immigrés", "%"),
    "single_parent_share": ("iris_families", ["single_parent"], ["families"],
                            "Part des familles monoparentales", "familles monoparentales", "%"),
    "large_family_share": ("iris_families", ["families_3_children", "families_4p_children"], ["families"],
                           "Part des familles de 3 enfants ou plus", "familles nombreuses", "%"),
    "living_alone_share": ("iris_families", ["pop_15p_alone"], ["pop_15p"],
                           "Part des personnes de 15 ans ou plus vivant seules", "personnes seules", "%"),
    "alone_80p_share": ("iris_families", ["pop_80p_alone"], ["pop_80p"],
                        "Part des 80 ans ou plus vivant seuls", "personnes de 80 ans ou plus seules", "%"),
    "social_housing_share": ("iris_housing", ["rp_social_housing"], ["main_res"],
                             "Part des résidences principales louées en HLM", "logements HLM", "%"),
    "renters_share": ("iris_housing", ["rp_renters"], ["main_res"],
                      "Part des ménages locataires", "résidences principales louées", "%"),
    "no_car_share": ("iris_housing", ["households"], ["households"],  # remplacé dans _values (ménages sans voiture)
                     "Part des ménages sans voiture", "ménages sans voiture", "%"),
    "no_diploma_share": ("iris_education", ["nscol_15p_no_dip"], ["nscol_15p"],
                         "Part des non-diplômés parmi les 15 ans ou plus non scolarisés", "sans diplôme", "%"),
    "higher_education_share": ("iris_education", ["nscol_15p_sup2", "nscol_15p_sup34", "nscol_15p_sup5"],
                               ["nscol_15p"], "Part des diplômés du supérieur parmi les 15 ans ou plus non scolarisés",
                               "diplômés du supérieur", "%"),
    "unemployment_rate": ("iris_activity", ["unemp_15_64"], ["active_15_64"],
                          "Taux de chômage des 15-64 ans (recensement)", "chômeurs", "%"),
    "youth_unemployment_rate": ("iris_activity", ["unemp_15_24"], ["active_15_24"],
                                "Taux de chômage des 15-24 ans (recensement)", "jeunes chômeurs", "%"),
    "women_activity_rate": ("iris_activity", ["active_women_15_64"], ["pop_women_15_64"],
                            "Taux d'activité des femmes de 15-64 ans", "femmes actives", "%"),
    "workers_employees_share": ("iris_activity", ["act_employees", "act_workers"], ["active_15_64"],
                                "Part des ouvriers et employés parmi les actifs", "ouvriers et employés actifs", "%"),
    # Tranches d'âge (2023 : « moins de 2 ans » et « 2-5 ans » au lieu de 0-2 et 3-5 ans ; la somme 0-5 ans est comparable)
    "under_6_share": ("iris_population", ["pop_0_2", "pop_3_5"], ["pop"], "Part des enfants de moins de 6 ans",
                      "enfants de moins de 6 ans", "%"),
    "age_6_10_share": ("iris_population", ["pop_6_10"], ["pop"], "Part des enfants de 6 à 10 ans",
                       "enfants de 6 à 10 ans", "%"),
    "age_11_17_share": ("iris_population", ["pop_11_17"], ["pop"], "Part des jeunes de 11 à 17 ans",
                        "jeunes de 11 à 17 ans", "%"),
    "age_18_24_share": ("iris_population", ["pop_18_24"], ["pop"], "Part des jeunes de 18 à 24 ans",
                        "jeunes de 18 à 24 ans", "%"),
    "age_65_79_share": ("iris_population", ["pop_65_79"], ["pop"], "Part des 65 à 79 ans", "personnes de 65 à 79 ans", "%"),
    "young_alone_share": ("iris_families", ["pop_15_24_alone"], ["pop_15_24"], "Part des 15-24 ans vivant seuls",
                          "jeunes de 15-24 ans vivant seuls", "%"),
    "alone_55_79_share": ("iris_families", ["pop_55_79_alone"], ["pop_55_79"], "Part des 55-79 ans vivant seuls",
                          "personnes de 55 à 79 ans vivant seules", "%"),
    "families_with_children_share": ("iris_families", ["couples_with_children", "single_parent"], ["families"],
                                     "Part des familles avec enfant(s) de moins de 25 ans", "familles avec enfants", "%"),
    "recent_movers_share": ("iris_housing", ["hh_moved_u2y"], ["households"],
                            "Part des ménages installés depuis moins de 2 ans", "ménages emménagés récemment", "%"),
    "foreigner_share": ("iris_population", ["pop_foreign"], ["pop"], "Part des étrangers", "étrangers", "%"),
    # Nouveau format Insee à l'IRIS (2023 seulement, scripts/import_iris_population_ages.py) : indice de jeunesse proche
    # de celui des communes (moins de 20 ans / 65 ans ou plus ; communes : 60 ans ou plus) ; moins de 2 ans
    "youth_ratio": ("iris_population", ["pop_lt20"], ["pop_ge65"],
                    "Indice de jeunesse (moins de 20 ans pour 100 personnes de 65 ans ou plus)", "moins de 20 ans", ""),
    "under_2_share": ("iris_population", ["pop_lt2"], ["pop"], "Part des enfants de moins de 2 ans",
                      "enfants de moins de 2 ans", "%"),
    "age_2_5_share": ("iris_population", ["pop_2_5"], ["pop"], "Part des enfants de 2 à 5 ans",
                      "enfants de 2 à 5 ans", "%"),
    # Diagnostic de quartier (indicateurs IRIS complémentaires, novembre 2026)
    "age_6_17_share": ("iris_population", ["pop_6_10", "pop_11_17"], ["pop"], "Part des 6-17 ans", "jeunes de 6 à 17 ans", "%"),
    "age_25_39_share": ("iris_population", ["pop_25_39"], ["pop"], "Part des 25-39 ans", "personnes de 25 à 39 ans", "%"),
    "aging_index": ("iris_population", ["pop_ge65"], ["pop_lt20"],
                    "Indice de vieillissement (65 ans ou plus pour 100 moins de 20 ans)", "65 ans ou plus", ""),
    "pop_growth": ("iris_population", ["pop"], ["pop"],  # calcul propre (_growth_values) : variation annuelle 2017-2023
                   "Évolution annuelle de la population", "habitants", "%/an"),
    "couples_no_children_share": ("iris_families", ["couples_no_children"], ["families"],
                                  "Part des couples sans enfant", "couples sans enfant", "%"),
    "large_family_share_with_children": ("iris_families", ["families_3_children", "families_4p_children"],
                                         ["families"],  # remplacé dans SPECIAL (familles avec enfants)
                                         "Part des familles de 3 enfants ou plus parmi les familles avec enfants",
                                         "familles nombreuses", "%"),
    "one_person_households_share": ("iris_families", ["pop_15p_alone"], ["pop_15p_alone"],  # CROSS : / ménages (logement)
                                    "Part des ménages d'une personne", "ménages d'une personne", "%"),
    "owners_share": ("iris_housing", ["rp_owners"], ["main_res"], "Part des propriétaires occupants",
                     "résidences principales occupées par leur propriétaire", "%"),
    "apartments_share": ("iris_housing", ["apartments"], ["housing_total"], "Part des appartements", "appartements", "%"),
    "small_dwellings_share": ("iris_housing", ["rp_1room", "rp_2rooms"], ["main_res"],
                              "Part des petits logements (1 ou 2 pièces)", "logements de 1 ou 2 pièces", "%"),
    "settled_10y_share": ("iris_housing", ["hh_moved_10py"], ["households"],
                          "Part des ménages installés depuis 10 ans ou plus", "ménages installés depuis 10 ans ou plus", "%"),
    "anchoring_ratio": ("iris_housing", ["hh_moved_10py"], ["hh_moved_u2y"],
                        "Ratio d'ancrage (ménages installés depuis 10 ans ou plus pour 100 arrivés depuis moins de 2 ans)",
                        "ménages installés depuis 10 ans ou plus", ""),
    "underoccupation_rate": ("iris_housing", ["rp_mild_underuse", "rp_heavy_underuse", "rp_extreme_underuse"],
                             ["rp_standard_occ", "rp_mild_underuse", "rp_heavy_underuse", "rp_extreme_underuse",
                              "rp_mild_overuse", "rp_heavy_overuse"],
                             "Part des résidences principales sous-occupées", "logements sous-occupés", "%"),
    "two_cars_share": ("iris_housing", ["hh_2p_cars"], ["households"], "Part des ménages avec deux voitures ou plus",
                       "ménages avec deux voitures ou plus", "%"),
    "employment_rate": ("iris_activity", ["employed_15_64"], ["pop_15_64"], "Taux d'emploi des 15-64 ans",
                        "actifs occupés de 15-64 ans", "%"),
    "part_time_share": ("iris_activity", ["salaried_15p_pt"], ["salaried_15p"], "Part des salariés à temps partiel",
                        "salariés à temps partiel", "%"),
    "work_other_commune_share": ("iris_activity", ["employed_15p"], ["employed_15p"],  # SPECIAL
                                 "Part des actifs occupés travaillant hors de leur commune de résidence",
                                 "actifs travaillant dans une autre commune", "%"),
    "walk_commute_share": ("iris_activity", ["transport_walk"], ["employed_15p"],
                           "Part des actifs occupés allant travailler à pied", "actifs allant travailler à pied", "%"),
    "car_commute_share": ("iris_activity", ["transport_car"], ["employed_15p"],
                          "Part des actifs occupés allant travailler en voiture", "actifs allant travailler en voiture", "%"),
    "overcrowding_rate": ("iris_housing", ["rp_mild_overuse", "rp_heavy_overuse"],
                          ["rp_standard_occ", "rp_mild_underuse", "rp_heavy_underuse", "rp_extreme_underuse",
                           "rp_mild_overuse", "rp_heavy_overuse"],
                          "Part des résidences principales suroccupées", "logements suroccupés", "%"),
    "vacancy_rate": ("iris_housing", ["vacant"], ["housing_total"], "Part des logements vacants", "logements vacants", "%"),
    "schooling_15_17_rate": ("iris_education", ["scol_15_17"], ["pop_15_17"], "Taux de scolarisation des 15-17 ans",
                             "jeunes de 15-17 ans scolarisés", "%"),
    "schooling_18_24_rate": ("iris_education", ["scol_18_24"], ["pop_18_24"], "Taux de scolarisation des 18-24 ans",
                             "jeunes de 18-24 ans scolarisés", "%"),
    "women_employment_rate": ("iris_activity", ["employed_women_15_64"], ["pop_women_15_64"],
                              "Taux d'emploi des femmes de 15-64 ans", "femmes en emploi", "%"),
    # 2023 : CDD, intérim, emplois aidés et apprentissage sont publiés ensemble (sal_cdd) ; la somme reste comparable
    "precarious_share": ("iris_activity", ["sal_cdd", "sal_interim", "sal_aided", "sal_appr"], ["salaried_15p"],
                         "Part des salariés hors CDI (CDD, intérim, emplois aidés, apprentissage)",
                         "salariés en contrat précaire", "%"),
    "transit_commute_share": ("iris_activity", ["transport_transit"], ["employed_15p"],
                              "Part des actifs occupés allant travailler en transports en commun",
                              "actifs en transports en commun", "%"),
}
# Rapports (et non parts) : pas d'effectif / total affiché pour les IRIS (le dénominateur n'est pas la population)
RATIOS = {"youth_ratio", "aging_index", "anchoring_ratio", "pop_growth"}
# Indicateurs dont le numérateur et le dénominateur viennent de deux tables (jointure par IRIS et millésime)
CROSS = {"one_person_households_share": ("SELECT f.iris_code, f.year, f.pop_15p_alone AS num, h.households AS den "
                                         "FROM iris_families f JOIN iris_housing h ON h.iris_code = f.iris_code "
                                         "AND h.year = f.year WHERE f.iris_code = ANY(:codes) ORDER BY f.year")}
# Échelle à seuils (cartes d'évolution, valeurs négatives possibles) : renvoyée telle quelle au tableau de bord
GROWTH_SCALE = {"breaks": [-1.0, -0.25, 0.25, 1.0], "legend_low": "Baisse", "legend_high": "Hausse"}

# Indicateurs de la table iris_indicators (hors recensement). additive : la commune est la somme de ses IRIS
# (count / total) ; sinon valeur de référence communale (geo_level 'COM'). den : dénominateur pris dans une table iris_*
# (colonne, millésime) quand la source ne le fournit pas.
EXTERNAL = {
    "median_income": {"label": "Revenu disponible médian par unité de consommation", "count_label": None, "unit": "€",
                      "additive": False, "source": "Insee, Filosofi (revenus disponibles, données à l'IRIS)"},
    "poverty_rate": {"label": "Taux de pauvreté (seuil de 60 % du niveau de vie médian)", "count_label": None, "unit": "%",
                     "additive": False, "source": "Insee, Filosofi (revenus disponibles, données à l'IRIS)"},
    "social_benefits_share": {"label": "Part des prestations sociales dans le revenu disponible", "count_label": None,
                              "unit": "%", "additive": False,
                              "source": "Insee, Filosofi (revenus disponibles, données à l'IRIS)"},
    "income_d1": {"label": "1er décile de niveau de vie (D1)", "count_label": None, "unit": "€", "additive": False,
                  "source": "Insee, Filosofi (revenus disponibles, données à l'IRIS)"},
    "interdecile_ratio": {"label": "Rapport interdécile D9/D1 du niveau de vie", "count_label": None, "unit": "",
                          "additive": False, "source": "Insee, Filosofi (revenus disponibles, données à l'IRIS)"},
    "c2s_free_rate": {"label": "Part des assurés bénéficiant de la complémentaire santé solidaire gratuite",
                      "count_label": "bénéficiaires de la C2S gratuite", "unit": "%", "additive": True,
                      "source": "Cnam, bénéficiaires du régime général au 1er janvier (diffusion Insee à l'IRIS)"},
    "social_turnover_rate": {"label": "Taux de rotation dans le parc social", "count_label": "emménagements (estimés)",
                             "unit": "%", "additive": True, "source": "SDES, RPLS au 1er janvier (diffusion Insee à l'IRIS)"},
    "social_vacancy_rate": {"label": "Taux de vacance dans le parc social", "count_label": "logements vacants (estimés)",
                            "unit": "%", "additive": True, "source": "SDES, RPLS au 1er janvier (diffusion Insee à l'IRIS)"},
    "job_seekers_abc": {"label": "Demandeurs d'emploi (catégories A, B, C) pour 100 actifs de 15-64 ans",
                        "count_label": "demandeurs d'emploi A, B, C", "unit": "%", "additive": True,
                        "den": ("iris_activity", "active_15_64", 2023),
                        "source": "France Travail / Insee, demandeurs d'emploi au 31 décembre (à l'IRIS) ; actifs : recensement 2023"},
}

# ménages sans voiture = ménages - ménages avec au moins une voiture
SPECIAL = {"no_car_share": ("CASE WHEN households IS NULL OR hh_1p_car IS NULL THEN NULL ELSE households - hh_1p_car END",
                            "households"),
           "large_family_share_with_children": ("COALESCE(families_3_children, 0) + COALESCE(families_4p_children, 0)",
                                                "families - families_0_children"),
           "work_other_commune_share": ("employed_15p - work_same_commune", "employed_15p")}


def _sum(cols):
    return " + ".join(f"COALESCE({c}, 0)" for c in cols)


class IrisMapService:

    def indicators(self):
        out = {k: {"label": v[3], "count_label": v[4], "unit": v[5], "table": v[0]} for k, v in INDICATORS.items()}
        out.update({k: {"label": v["label"], "count_label": v["count_label"], "unit": v["unit"], "table": "iris_indicators"}
                    for k, v in EXTERNAL.items()})
        return out

    def _external_values(self, key, iris_codes, com_code):
        meta = EXTERNAL[key]
        db = SessionLocal()
        try:
            rows = db.execute(text(
                "SELECT geo_level, geo_code, year, value, count, total FROM iris_indicators "
                "WHERE indicator = :k AND ((geo_level = 'IRIS' AND geo_code = ANY(:codes)) "
                "OR (geo_level = 'COM' AND geo_code = :com)) ORDER BY year"),
                {"k": key, "codes": list(iris_codes), "com": com_code}).fetchall()
            den = {}
            if meta.get("den"):
                table, col, year = meta["den"]
                den = {r[0]: float(r[1]) for r in db.execute(text(
                    f"SELECT iris_code, {col} FROM {table} WHERE year = :y AND iris_code = ANY(:codes)"),
                    {"y": year, "codes": list(iris_codes)}).fetchall() if r[1] is not None}
        finally:
            db.close()
        values, commune = {}, {}
        for r in rows:
            count = float(r.count) if r.count is not None else None
            total = float(r.total) if r.total is not None else den.get(r.geo_code) if r.geo_level == "IRIS" else None
            value = float(r.value) if r.value is not None else (
                round(count / total * 100, 1) if count is not None and total else None)
            item = {"value": round(value, 1) if value is not None and meta["unit"] != "€" else value,
                    "count": round(count) if count is not None else None,
                    "total": round(total) if total is not None else None}
            if r.geo_level == "IRIS":
                values.setdefault(r.geo_code, {})[r.year] = item
            else:
                commune[r.year] = item
        return values, commune

    def geometries(self, com_code: str) -> list:
        db = SessionLocal()
        try:
            rows = db.execute(text(
                "SELECT iris_code, com_code, iris_name, iris_type, label_lon, label_lat, geometry "
                "FROM iris_geometries WHERE com_parent = :c OR com_code = :c ORDER BY iris_code"), {"c": com_code}).fetchall()
            return [{"iris_code": r.iris_code, "com_code": r.com_code, "iris_name": r.iris_name, "iris_type": r.iris_type,
                     "label": [r.label_lon, r.label_lat], "geometry": json.loads(r.geometry)} for r in rows]
        finally:
            db.close()

    def _growth_values(self, iris_codes):
        """Variation annuelle moyenne de la population entre le premier et le dernier millésime IRIS (2017 → 2023) ;
        count = population finale, total = population initiale (la valeur communale se recalcule sur les sommes)."""
        db = SessionLocal()
        try:
            rows = db.execute(text("SELECT iris_code, year, pop FROM iris_population WHERE iris_code = ANY(:codes)"),
                              {"codes": list(iris_codes)}).fetchall()
        finally:
            db.close()
        by = {}
        for r in rows:
            by.setdefault(r.iris_code, {})[r.year] = r.pop
        years = sorted({r.year for r in rows})
        if len(years) < 2:
            return {}
        y0, y1 = years[0], years[-1]
        out = {}
        for code, d in by.items():
            p0, p1 = d.get(y0), d.get(y1)
            ok = p0 and p1 and p0 > 0 and p1 > 0
            out[code] = {y1: {"value": round(((p1 / p0) ** (1 / (y1 - y0)) - 1) * 100, 2) if ok else None,
                              "count": round(p1) if p1 is not None else None,
                              "total": round(p0) if p0 is not None else None, "start_year": y0}}
        return out

    def _values(self, key, iris_codes):
        if key == "pop_growth":
            return self._growth_values(iris_codes)
        table, num, den, *_ = INDICATORS[key]
        num_sql, den_sql = SPECIAL.get(key, (_sum(num), _sum(den)))
        sql = CROSS.get(key) or (f"SELECT iris_code, year, {num_sql} AS num, {den_sql} AS den FROM {table} "
                                 f"WHERE iris_code = ANY(:codes) ORDER BY year")
        db = SessionLocal()
        try:
            rows = db.execute(text(sql), {"codes": list(iris_codes)}).fetchall()
        finally:
            db.close()
        out = {}
        for r in rows:
            num_v = float(r.num) if r.num is not None else None
            den_v = float(r.den) if r.den is not None else None
            out.setdefault(r.iris_code, {})[r.year] = {
                "value": round(num_v / den_v * 100, 1) if num_v is not None and den_v else None,
                "count": round(num_v) if num_v is not None else None,
                "total": round(den_v) if den_v is not None else None,
            }
        return out

    def commune_map(self, com_code: str, indicator: str) -> Optional[dict]:
        if indicator not in INDICATORS and indicator not in EXTERNAL:
            return {"error": f"Indicateur inconnu : {indicator}. Disponibles : {', '.join(list(INDICATORS) + list(EXTERNAL))}"}
        features = self.geometries(com_code)
        if not features:
            return None
        external = indicator in EXTERNAL
        if external:
            values, commune_ref = self._external_values(indicator, [f["iris_code"] for f in features], com_code)
        else:
            values = self._values(indicator, [f["iris_code"] for f in features])
        # millésimes où au moins un IRIS a une valeur (les tranches du nouveau format n'existent qu'en 2023)
        years = sorted({y for v in values.values() for y, d in v.items() if (d or {}).get("value") is not None})
        values = {c: {y: d for y, d in v.items() if y in years} for c, v in values.items()}
        if len(years) > 2:  # premier et dernier millésimes seulement (évolution)
            years = [years[0], years[-1]]
            values = {c: {y: v for y, v in d.items() if y in years} for c, d in values.items()}
        commune = {}
        for y in years:
            if external and not EXTERNAL[indicator]["additive"]:
                commune[y] = commune_ref.get(y, {"value": None, "count": None, "total": None})
                continue
            cnt = sum((values.get(f["iris_code"], {}).get(y, {}) or {}).get("count") or 0 for f in features)
            tot = sum((values.get(f["iris_code"], {}).get(y, {}) or {}).get("total") or 0 for f in features)
            if indicator == "pop_growth":
                y0 = next((d.get(y, {}).get("start_year") for d in values.values() if d.get(y)), None)
                v = round(((cnt / tot) ** (1 / (y - y0)) - 1) * 100, 2) if tot and cnt and y0 else None
                commune[y] = {"value": v, "count": cnt, "total": tot}
                continue
            commune[y] = {"value": round(cnt / tot * 100, 1) if tot else None, "count": cnt, "total": tot}
        for f in features:
            f["values"] = values.get(f["iris_code"], {})
        if external:
            m = EXTERNAL[indicator]
            ind = {"key": indicator, "label": m["label"], "count_label": m["count_label"], "unit": m["unit"],
                   "additive": m["additive"]}
            source = m["source"] + " ; IGN-Insee, contours IRIS 2024"
        else:
            meta = INDICATORS[indicator]
            ind = {"key": indicator, "label": meta[3], "count_label": meta[4], "unit": meta[5],
                   "additive": indicator not in RATIOS}
            source = "Insee, recensements de la population (bases infracommunales IRIS) ; IGN-Insee, contours IRIS 2024"
        extra = {}
        if indicator == "pop_growth" and years:
            y0 = next((d.get(years[-1], {}).get("start_year") for d in values.values() if d.get(years[-1])), None)
            ind["label"] = f"Évolution annuelle de la population {y0}-{years[-1]}"
            extra = dict(GROWTH_SCALE, color_note="Couleur : taux de variation annuel moyen ; entre −0,25 % et +0,25 % "
                                                  "par an, la population est quasi stable.")
        return {
            **extra,
            "commune": {"code": com_code, "values": commune},
            "indicator": ind,
            "years": years,
            "latest_year": years[-1] if years else None,
            "irisee": any(f["iris_type"] != "commune" for f in features) and len(features) > 1,
            "features": features,
            "source": source,
        }
