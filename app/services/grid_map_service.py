"""
Cartes carroyées : Insee, Filosofi 2021, carreaux de 1 km (table grid_filosofi_1km, scripts/import_grid_filosofi.py).

Pour une commune : tous les carreaux habités qui la touchent (un carreau à cheval sur plusieurs communes est renvoyé
entier pour chacune), avec leurs quatre coins en longitude / latitude (calculés depuis l'identifiant LAEA), la valeur
de l'indicateur, les effectifs et l'indicateur d'imputation ; valeur de référence = ensemble de ces carreaux ; valeur
France métropolitaine = ensemble des carreaux ; contours des IRIS de la commune pour le repérage.
"""
import json
import logging

from sqlalchemy import text

from app.database import SessionLocal
from app.utils.laea import laea_to_wgs84

logger = logging.getLogger(__name__)

SIZE = 1000
# clé : (numérateur, dénominateur, libellé, libellé de l'effectif, unité, facteur)
INDICATORS = {
    "living_standard": ("ind_snv", "ind", "Niveau de vie moyen des habitants", None, "€", 1),
    "poor_households_share": ("men_pauv", "men", "Part des ménages pauvres", "ménages pauvres", "%", 100),
    "single_parent_share": ("men_fmp", "men", "Part des ménages monoparentaux", "ménages monoparentaux", "%", 100),
    "social_housing_share": ("log_soc", "men", "Part des ménages en logement social", "ménages en logement social",
                             "%", 100),
    "age_0_3_share": ("ind_0_3", "ind", "Part des enfants de 0 à 3 ans", "enfants de 0 à 3 ans", "%", 100),
    "age_80p_share": ("ind_80p", "ind", "Part des 80 ans ou plus", "personnes de 80 ans ou plus", "%", 100),
}
SOURCE = ("Insee, Filosofi 2021, revenus, pauvreté et niveau de vie — données carroyées (carreaux de 1 km) ; "
          "IGN-Insee, contours IRIS 2024")
_FRANCE = {}


def _ratio(num, den, factor):
    if num is None or not den:
        return None
    return round(num / den * factor, 1 if factor == 100 else 0)


class GridMapService:
    def indicators(self):
        return {k: {"label": v[2], "count_label": v[3], "unit": v[4]} for k, v in INDICATORS.items()}

    def _france(self, db, key):
        if key not in _FRANCE:
            num, den, *_rest, factor = INDICATORS[key]
            r = db.execute(text(f"SELECT sum({num}), sum({den}) FROM grid_filosofi_1km")).fetchone()
            _FRANCE[key] = _ratio(float(r[0]) if r[0] is not None else None, float(r[1]) if r[1] else None, factor)
        return _FRANCE[key]

    def commune_map(self, com_code, indicator):
        if indicator not in INDICATORS:
            return {"error": f"Indicateur inconnu : {indicator}. Disponibles : {', '.join(INDICATORS)}"}
        num, den, label, count_label, unit, factor = INDICATORS[indicator]
        code = str(com_code).zfill(5)
        db = SessionLocal()
        try:
            rows = db.execute(text(
                f"SELECT idcar, x, y, imputed, communes, ind, men, {num} AS num, {den} AS den "
                f"FROM grid_filosofi_1km WHERE communes @> ARRAY[:c]::varchar[] ORDER BY y DESC, x"),
                {"c": code}).fetchall()
            if not rows:
                return {"error": f"Aucun carreau habité pour la commune {code}"}
            france = self._france(db, indicator)
            outline = db.execute(text(
                "SELECT geometry FROM iris_geometries WHERE com_parent = :c OR com_code = :c"), {"c": code}).fetchall()
        finally:
            db.close()
        cells, tot_num, tot_den = [], 0.0, 0.0
        for r in rows:
            corners = [laea_to_wgs84(r.x + dx, r.y + dy) for dx, dy in ((0, 0), (SIZE, 0), (SIZE, SIZE), (0, SIZE))]
            n = float(r.num) if r.num is not None else None
            d = float(r.den) if r.den is not None else None
            if n is not None and d:
                tot_num += n
                tot_den += d
            cells.append({
                "id": r.idcar, "corners": [[round(lat, 6), round(lon, 6)] for lon, lat in corners],
                "value": _ratio(n, d, factor), "count": round(n) if n is not None and unit != "€" else None,
                "total": round(d) if d is not None else None, "population": round(float(r.ind or 0)),
                "imputed": r.imputed == 1, "shared": len(r.communes) > 1, "communes": list(r.communes),
            })
        return {
            "commune": code,
            "indicator": {"key": indicator, "label": label, "count_label": count_label, "unit": unit,
                          "denominator": "ménages" if den == "men" else "habitants"},
            "year": 2021,
            "reference": _ratio(tot_num, tot_den, factor),
            "france": france,
            "cells": cells,
            "outline": [json.loads(o.geometry) for o in outline],
            "source": SOURCE,
        }
