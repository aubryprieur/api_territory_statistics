"""
Cartes IRIS : contours (iris_geometries) et indicateurs par IRIS pour une commune, aux millésimes disponibles
(2017, 2022), avec la valeur de la commune calculée sur la somme de ses IRIS (même source, même millésime).

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
}
# ménages sans voiture = ménages - ménages avec au moins une voiture
SPECIAL = {"no_car_share": ("CASE WHEN households IS NULL OR hh_1p_car IS NULL THEN NULL ELSE households - hh_1p_car END",
                            "households")}


def _sum(cols):
    return " + ".join(f"COALESCE({c}, 0)" for c in cols)


class IrisMapService:

    def indicators(self):
        return {k: {"label": v[3], "count_label": v[4], "unit": v[5], "table": v[0]} for k, v in INDICATORS.items()}

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

    def _values(self, key, iris_codes):
        table, num, den, *_ = INDICATORS[key]
        num_sql, den_sql = SPECIAL.get(key, (_sum(num), _sum(den)))
        db = SessionLocal()
        try:
            rows = db.execute(text(
                f"SELECT iris_code, year, {num_sql} AS num, {den_sql} AS den FROM {table} "
                f"WHERE iris_code = ANY(:codes) ORDER BY year"), {"codes": list(iris_codes)}).fetchall()
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
        if indicator not in INDICATORS:
            return {"error": f"Indicateur inconnu : {indicator}. Disponibles : {', '.join(INDICATORS)}"}
        features = self.geometries(com_code)
        if not features:
            return None
        values = self._values(indicator, [f["iris_code"] for f in features])
        years = sorted({y for v in values.values() for y in v})
        commune = {}
        for y in years:
            cnt = sum((values.get(f["iris_code"], {}).get(y, {}) or {}).get("count") or 0 for f in features)
            tot = sum((values.get(f["iris_code"], {}).get(y, {}) or {}).get("total") or 0 for f in features)
            commune[y] = {"value": round(cnt / tot * 100, 1) if tot else None, "count": cnt, "total": tot}
        for f in features:
            f["values"] = values.get(f["iris_code"], {})
        meta = INDICATORS[indicator]
        return {
            "commune": {"code": com_code, "values": commune},
            "indicator": {"key": indicator, "label": meta[3], "count_label": meta[4], "unit": meta[5]},
            "years": years,
            "latest_year": years[-1] if years else None,
            "irisee": any(f["iris_type"] != "commune" for f in features) and len(features) > 1,
            "features": features,
            "source": "Insee, recensements de la population (bases infracommunales IRIS) ; IGN-Insee, contours IRIS 2024",
        }
