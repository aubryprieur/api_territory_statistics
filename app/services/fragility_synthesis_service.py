"""
Synthèse des fragilités d'une commune (tables fragility_synthesis et fragility_reference,
scripts/import_fragility_synthesis.py ; catalogue app/fragility_catalog.py).

Pour chaque indicateur : valeur, effectif, millésime, valeur France, médiane de la catégorie de densité, rang national,
rang dans la catégorie de densité et rang parmi les communes de l'EPCI, calculé à la volée (0 = moins touchée,
100 = plus touchée). Pour chaque enjeu : nombre d'indicateurs
disponibles, en alerte (parmi les 20 % de communes de même densité les plus touchées) et points forts (parmi les 20 %
les moins touchées), niveau fort / modéré / faible / non évaluable.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.fragility_catalog import (ALERT_THRESHOLD, CONTEXT_GROUP_KEYS, CONTEXT_GROUPS, CONTEXT_INDICATORS, INDICATORS,
                                   STRENGTH_THRESHOLD, THEMES)
from app.models import FragilityReference, FragilitySynthesis, GeoCode

SOURCE = ("Calcul à partir des données de l'API (INSEE, Cnaf, Dares, DGFiP, Observatoire des situations de fragilité, "
          "DREES, INJEP, SSMSI) ; grille communale de densité INSEE à 7 niveaux (2025)")


def theme_level(available, alerts, expected):
    if expected == 0 or available < expected / 2:
        return "not_evaluable"
    share = alerts / available
    if share >= 0.5:
        return "high"
    if share >= 0.25:
        return "moderate"
    return "low"


def epci_ranks(db, code, keys):
    """Rang de la commune parmi les communes de son EPCI, calculé à la volée sur fragility_synthesis.
    Retourne (infos EPCI, {clé: (rang 0-100, position, n, médiane)}). Même convention que l'import : pour « up » et
    « neutral », 100 = valeur la plus élevée ; pour « down », 100 = valeur la plus faible. Position : 1 = la plus touchée
    (ou la valeur la plus élevée pour un indicateur de structure)."""
    geo = db.query(GeoCode).filter(GeoCode.codgeo == code).first()
    if geo is None or not geo.epci or geo.epci in ("ZZZZZZZZZ", "ZZZZZZZZ"):
        return None, {}
    members = [c for (c,) in db.query(GeoCode.codgeo).filter(GeoCode.epci == geo.epci).all()]
    if len(members) < 2:
        return None, {}
    rows = db.query(FragilitySynthesis.geo_code, FragilitySynthesis.data).filter(
        FragilitySynthesis.geo_code.in_(members)).all()
    info = {"code": geo.epci, "label": geo.libepci, "communes": len(members)}
    out = {}
    for key, direction in keys:
        vals = {c: d[key][0] for c, d in rows if d and d.get(key) and d[key][0] is not None}
        own = vals.get(code)
        n = len(vals)
        if own is None or n < 2:
            continue
        sign = -1 if direction == "down" else 1
        lower = sum(1 for v in vals.values() if sign * v < sign * own)
        equal = sum(1 for v in vals.values() if v == own)
        avg_rank = lower + (equal + 1) / 2          # rang moyen 1..n, comme pandas rank(method="average")
        pct = round((avg_rank - 0.5) / n * 100, 1)
        position = n - lower - equal + 1             # 1 = valeur la plus « touchée »
        srt = sorted(vals.values())
        median = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
        out[key] = (pct, position, n, round(median, 2))
    return info, out


class FragilitySynthesisService:
    def by_commune(self, code):
        code = str(code).zfill(5)
        db = SessionLocal()
        try:
            row = db.query(FragilitySynthesis).filter(FragilitySynthesis.geo_code == code).first()
            if row is None:
                return {"error": f"Aucune synthèse des fragilités pour la commune {code}"}
            scopes = ["FR"] + ([row.dens7] if row.dens7 else [])
            refs = {(r.indicator, r.scope): r for r in
                    db.query(FragilityReference).filter(FragilityReference.scope.in_(scopes)).all()}
            data = row.data or {}
            epci, epci_rk = epci_ranks(db, code, [(i["key"], i["direction"]) for i in INDICATORS + CONTEXT_INDICATORS])
            indicators = []
            context = []
            for ind in INDICATORS + CONTEXT_INDICATORS:
                fr = refs.get((ind["key"], "FR"))
                dens = refs.get((ind["key"], row.dens7)) if row.dens7 else None
                v = data.get(ind["key"])
                item = {k: ind[k] for k in ("key", "label", "theme", "direction", "unit", "tab", "need")}
                item.update({
                    "year": fr.year if fr else None,
                    "value": v[0] if v else None, "count": v[1] if v else None,
                    "rank_france": v[2] if v else None, "rank_density": v[3] if v else None,
                    "france_value": fr.france_value if fr else None,
                    "density_median": dens.median if dens else None,
                    "density_n": dens.n if dens else None, "france_n": fr.n if fr else None,
                })
                ek = epci_rk.get(ind["key"])
                item.update({"rank_epci": ek[0] if ek else None, "epci_position": ek[1] if ek else None,
                             "epci_n": ek[2] if ek else None, "epci_median": ek[3] if ek else None})
                r = item["rank_density"] if item["rank_density"] is not None else item["rank_france"]
                judged = ind["direction"] != "neutral"
                item["alert"] = judged and r is not None and r >= ALERT_THRESHOLD
                item["strength"] = judged and r is not None and r <= STRENGTH_THRESHOLD and not ind["need"]
                if ind["context"]:
                    context.append(item)
                else:
                    indicators.append(item)
            themes = []
            for key, label in THEMES.items():
                items = [i for i in indicators if i["theme"] == key]
                avail = [i for i in items if i["value"] is not None]
                alerts = [i for i in avail if i["alert"]]
                themes.append({"key": key, "label": label, "kind": "core", "expected": len(items),
                               "available": len(avail), "alerts": len(alerts),
                               "strengths": sum(1 for i in avail if i["strength"]),
                               "level": theme_level(len(avail), len(alerts), len(items))})
            # Enjeux complémentaires (onglets de contexte) : niveau calculé sur leurs indicateurs jugés (hors structure),
            # sans entrer dans le décompte de la synthèse (certains indicateurs sont partagés avec les enjeux principaux)
            by_key = {i["key"]: i for i in indicators + context}
            for key, (label, tab) in CONTEXT_GROUPS.items():
                items = [by_key[k] for k in CONTEXT_GROUP_KEYS.get(key, []) if k in by_key]
                judged = [i for i in items if i["direction"] != "neutral"]
                avail = [i for i in judged if i["value"] is not None]
                alerts = [i for i in avail if i["alert"]]
                level = theme_level(len(avail), len(alerts), len(judged)) if judged else "context"
                themes.append({"key": key, "label": label, "kind": "context", "tab": tab, "expected": len(judged),
                               "available": len(avail), "alerts": len(alerts),
                               "strengths": sum(1 for i in avail if i["strength"]), "level": level})
            return {
                "territory": {"level": "COM", "code": code},
                "density": {"code": row.dens7, "label": row.dens7_label},
                "epci": epci,
                "population": row.population,
                "thresholds": {"alert": ALERT_THRESHOLD, "strength": STRENGTH_THRESHOLD},
                "source": SOURCE,
                "themes": themes,
                "indicators": indicators,
                "context_indicators": context,
                "context_groups": [{"key": k, "label": lbl, "tab": tab, "indicators": CONTEXT_GROUP_KEYS.get(k, [])}
                                   for k, (lbl, tab) in CONTEXT_GROUPS.items()],
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()
