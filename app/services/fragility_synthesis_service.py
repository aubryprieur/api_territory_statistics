"""
Synthèse des fragilités d'une commune (tables fragility_synthesis et fragility_reference,
scripts/import_fragility_synthesis.py ; catalogue app/fragility_catalog.py).

Pour chaque indicateur : valeur, effectif, millésime, valeur France, médiane de la catégorie de densité, rang national
et rang dans la catégorie de densité (0 = moins touchée, 100 = plus touchée). Pour chaque enjeu : nombre d'indicateurs
disponibles, en alerte (parmi les 20 % de communes de même densité les plus touchées) et points forts (parmi les 20 %
les moins touchées), niveau fort / modéré / faible / non évaluable.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.fragility_catalog import ALERT_THRESHOLD, CONTEXT_INDICATORS, INDICATORS, STRENGTH_THRESHOLD, THEMES
from app.models import FragilityReference, FragilitySynthesis

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
                r = item["rank_density"] if item["rank_density"] is not None else item["rank_france"]
                item["alert"] = r is not None and r >= ALERT_THRESHOLD
                item["strength"] = r is not None and r <= STRENGTH_THRESHOLD and not ind["need"]
                if ind["context"]:
                    item["alert"] = item["strength"] = False
                    context.append(item)
                else:
                    indicators.append(item)
            themes = []
            for key, label in THEMES.items():
                items = [i for i in indicators if i["theme"] == key]
                avail = [i for i in items if i["value"] is not None]
                alerts = [i for i in avail if i["alert"]]
                themes.append({"key": key, "label": label, "expected": len(items), "available": len(avail),
                               "alerts": len(alerts), "strengths": sum(1 for i in avail if i["strength"]),
                               "level": theme_level(len(avail), len(alerts), len(items))})
            return {
                "territory": {"level": "COM", "code": code},
                "density": {"code": row.dens7, "label": row.dens7_label},
                "population": row.population,
                "thresholds": {"alert": ALERT_THRESHOLD, "strength": STRENGTH_THRESHOLD},
                "source": SOURCE,
                "themes": themes,
                "indicators": indicators,
                "context_indicators": context,
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()
