"""
Créations d'entreprises — Insee, SIDE (fichiers détail « Créations d'entreprises et d'établissements pour l'année
N »), table business_creations_by_territory (scripts/import_business_creations_by_territory.py).

Créations d'entreprises (unités légales) localisées à la commune du siège, micro-entrepreneurs compris :
  - par an et pour 1 000 habitants (population du recensement le plus proche : 2017 pour 2019, 2023 ensuite) ;
  - moyenne annuelle sur les cinq dernières années, pour 1 000 habitants ;
  - sur ces cinq ans : part des entreprises individuelles, des créations avec salariés, et par grand secteur.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import BusinessCreationsByTerritory, PopulationByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct

SECTORS = {
    "sector_industry": "Industrie",
    "sector_construction": "Construction",
    "sector_trade": "Commerce, transports, hébergement et restauration",
    "sector_business_services": "Services aux entreprises (information, finance, immobilier, conseil, services administratifs)",
    "sector_personal_services": "Enseignement, santé, action sociale et services aux personnes",
}
FIELDS = ["created", "created_individual", "created_company", "created_employer"] + list(SECTORS)
SOURCE = ("Insee, Système d'information sur la démographie d'entreprises (SIDE), créations d'entreprises "
          "2019-2025 ; Insee, recensement de la population")
WINDOW = 5


def census_year(year, available):
    return min(available, key=lambda c: (abs(c - year), -c)) if available else None


def per_1000(value, pop):
    if value is None or not pop:
        return None
    return round(value / pop * 1000, 2)


class BusinessCreationsService(TerritoryStatsService):
    MODEL = BusinessCreationsByTerritory
    DATA_KEY = "business_creations_data"
    LABEL = "créations d'entreprises"
    EXTRA = {"sectors": SECTORS, "source": SOURCE}

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

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        data = result[self.DATA_KEY]
        pops = self._population(level, code)
        for y, d in data.items():
            c = census_year(y, list(pops))
            d["census_year"] = c
            d["created_per_1000"] = per_1000(d.get("created"), pops.get(c))
            d["individual_share"] = pct(d.get("created_individual"), d.get("created"))

        years = sorted(data)[-WINDOW:]
        sums = {f: sum(data[y].get(f) or 0 for y in years) for f in FIELDS}
        latest_pop = pops.get(max(pops)) if pops else None
        avg = round(sums["created"] / len(years), 1) if years else None
        result["summary"] = {
            "period": f"{years[0]}-{years[-1]}" if years else None,
            "population": latest_pop, "population_year": max(pops) if pops else None,
            "total": sums["created"], "avg": avg, "avg_per_1000": per_1000(avg, latest_pop),
            "individual_share": pct(sums["created_individual"], sums["created"]),
            "employer_share": pct(sums["created_employer"], sums["created"]),
            "sector_shares": {s: pct(sums[s], sums["created"]) for s in SECTORS},
        }
        result["evolution"] = {}
        return result
