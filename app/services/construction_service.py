"""
Construction neuve de logements — SDES, base Sitadel (« Données annuelles communales — Logements », septembre 2026),
table construction_by_territory (scripts/import_construction_by_territory.py).

Indicateurs pour l'analyse des besoins sociaux :
  - logements commencés et autorisés par an, pour 1 000 habitants (population du recensement le plus proche :
    2012 pour 2013-2014, 2017 pour 2015-2019, 2023 à partir de 2020) ;
  - moyennes annuelles sur les cinq dernières années publiées (commencés 2020-2024, autorisés 2021-2025) ;
  - répartition des logements commencés sur ces cinq ans : individuel pur, individuel groupé, collectif,
    résidence (étudiants, personnes âgées, tourisme…).
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import ConstructionByTerritory, PopulationByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct

TYPES = {"ind_pure": "Individuel pur", "ind_group": "Individuel groupé", "collective": "Collectif",
         "residence": "Résidence (étudiants, seniors, tourisme…)"}
FIELDS = [f"{k}_{t}" for k in ("authorised", "started") for t in ["total"] + list(TYPES)]
SOURCE = ("SDES, base Sitadel — logements autorisés et commencés, données annuelles communales (septembre 2026) ; "
          "Insee, recensement de la population")
WINDOW = 5


def census_year(year, available):
    """Millésime du recensement le plus proche (2012, 2017, 2023)."""
    return min(available, key=lambda c: (abs(c - year), -c)) if available else None


def per_1000(value, pop):
    if value is None or not pop:
        return None
    return round(value / pop * 1000, 2)


class ConstructionService(TerritoryStatsService):
    MODEL = ConstructionByTerritory
    DATA_KEY = "construction_data"
    LABEL = "construction neuve"
    EXTRA = {"types": TYPES, "source": SOURCE}

    def year_data(self, row):
        return {f: num(getattr(row, f)) for f in FIELDS}

    def _population(self, level, code):
        db = SessionLocal()
        try:
            rows = (db.query(PopulationByTerritory.year, PopulationByTerritory.pop)
                    .filter(PopulationByTerritory.geo_level == level, PopulationByTerritory.geo_code == str(code)).all())
            return {y: num(p) for y, p in rows if num(p)}
        except SQLAlchemyError:
            return {}
        finally:
            db.close()

    def _window(self, data, key, years):
        values = [data[y][key] for y in years if data[y].get(key) is not None]
        return sum(values) if len(values) == len(years) and years else None

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        data = result[self.DATA_KEY]
        pops = self._population(level, code)
        for y, d in data.items():
            c = census_year(y, list(pops))
            d["census_year"] = c
            d["started_per_1000"] = per_1000(d.get("started_total"), pops.get(c))
            d["authorised_per_1000"] = per_1000(d.get("authorised_total"), pops.get(c))

        latest_pop = pops.get(max(pops)) if pops else None
        summary = {"population": latest_pop, "population_year": max(pops) if pops else None}
        for kind in ("started", "authorised"):
            years = sorted(y for y in data if data[y].get(f"{kind}_total") is not None)[-WINDOW:]
            total = self._window(data, f"{kind}_total", years)
            avg = round(total / len(years), 1) if total is not None else None
            summary[kind] = {
                "period": f"{years[0]}-{years[-1]}" if years else None,
                "total": total, "avg": avg, "avg_per_1000": per_1000(avg, latest_pop),
                "shares": {t: pct(self._window(data, f"{kind}_{t}", years), total) for t in TYPES},
            }
        result["summary"] = summary
        result["started_years"] = sorted(y for y in data if data[y].get("started_total") is not None)
        result["evolution"] = {}
        return result
