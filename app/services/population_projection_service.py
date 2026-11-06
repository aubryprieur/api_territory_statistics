"""
Projections démographiques par commune (table population_projection, scripts/import_population_projection.py).
Méthode des composantes par cohortes simplifiée, de 2023 à 2033 : voir le docstring du script d'import.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import GeoCode, PopulationProjection

GROUPS = {"0_2": "Moins de 3 ans", "3_5": "3-5 ans", "6_10": "6-10 ans", "11_14": "11-14 ans", "15_17": "15-17 ans",
          "18_24": "18-24 ans", "60_74": "60-74 ans", "75_84": "75-84 ans", "85p": "85 ans ou plus",
          "total": "Population totale"}
# Fiabilité à 10 ans : dépend surtout de la part des personnes déjà nées et des migrations
RELIABILITY = {"births": "moyenne", "0_2": "moyenne", "3_5": "moyenne", "6_10": "bonne", "11_14": "bonne",
               "15_17": "bonne", "18_24": "moyenne", "60_74": "bonne", "75_84": "bonne", "85p": "bonne",
               "total": "bonne"}
SOURCE = ("Calcul à partir des recensements 2017, 2022 et 2023 (Insee), de l'état civil (naissances domiciliées "
          "2014-2023) et de la table de mortalité de l'Insee (France métropolitaine)")
METHOD = ("Projection par cohortes : chaque année, la population vieillit d'un an, les décès sont appliqués selon la "
          "table de mortalité nationale, les arrivées et départs selon le profil par âge observé dans la commune entre "
          "les recensements 2017 et 2022 (rapproché du département pour les petits effectifs), et les naissances selon "
          "le taux de natalité de la commune (naissances 2021-2023 rapportées aux femmes de 15 à 49 ans), appliqué aux "
          "femmes de 15 à 49 ans projetées. Point de départ : 1er janvier 2023, recalé sur le recensement 2023.")


class PopulationProjectionService:
    def by_commune(self, code):
        code = str(code).zfill(5)
        db = SessionLocal()
        try:
            row = db.query(PopulationProjection).filter(PopulationProjection.geo_code == code).first()
            if row is None:
                return {"error": f"Aucune projection pour la commune {code}"}
            return {"territory": {"level": "COM", "code": code}, "base_year": row.base_year,
                    "population": row.population, "labels": GROUPS, "reliability": RELIABILITY,
                    "source": SOURCE, "method": METHOD, **row.data}
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def by_epci(self, epci):
        """Projection d'un EPCI : somme des projections de ses communes (effectifs par âge, naissances, pyramide)."""
        db = SessionLocal()
        try:
            codes = [c for (c,) in db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()]
            rows = db.query(PopulationProjection).filter(PopulationProjection.geo_code.in_(codes)).all() if codes else []
            if not rows:
                return {"error": f"Aucune projection pour l'EPCI {epci}"}
            datas = [r.data for r in rows if r.data]
            first = datas[0]

            def add_lists(lists):
                lists = [l for l in lists if isinstance(l, list)]
                if not lists:
                    return None
                n = max(len(l) for l in lists)
                return [round(sum((l[i] or 0) for l in lists if i < len(l)), 1) for i in range(n)]

            def add_groups(key):
                keys = {g for d in datas for g in (d.get(key) or {})}
                return {g: [int(round(v)) for v in (add_lists([(d.get(key) or {}).get(g) for d in datas]) or [])] for g in keys}

            births = {"years": first["births"]["years"]}
            for k in ("trend", "low", "high", "no_migration"):
                births[k] = add_lists([d["births"].get(k) for d in datas])
            observed = {}
            for d in datas:
                for y, v in (d["births"].get("observed") or {}).items():
                    if v is not None:
                        observed[y] = observed.get(y, 0) + v
            births["observed"] = observed
            pop = sum(r.population or 0 for r in rows)
            spread = [(d.get("births_spread_pct"), r.population or 0) for d, r in zip(datas, rows) if d.get("births_spread_pct") is not None]
            data = {
                "base_year": first["base_year"], "years": first["years"], "mortality_table": first.get("mortality_table"),
                "groups": add_groups("groups"), "no_migration": add_groups("no_migration"),
                "low": add_groups("low"), "high": add_groups("high"), "births": births,
                "fertility_per_1000_women": None, "births_test_error_pct": None,
                "births_spread_pct": round(sum(s * w for s, w in spread) / sum(w for _, w in spread)) if spread and sum(w for _, w in spread) else None,
                "migration_source": "communes", "migration_annual_pct": None,
                "pyramid": {"year": first["pyramid"]["year"], "groups": first["pyramid"]["groups"],
                            "men": [int(round(v)) for v in add_lists([d["pyramid"].get("men") for d in datas])],
                            "women": [int(round(v)) for v in add_lists([d["pyramid"].get("women") for d in datas])]},
            }
            return {"territory": {"level": "EPCI", "code": str(epci)}, "base_year": first["base_year"],
                    "population": pop, "communes": len(rows), "labels": GROUPS, "reliability": RELIABILITY,
                    "source": SOURCE, "method": METHOD + " Intercommunalité : somme des projections de ses communes.",
                    **data}
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()
