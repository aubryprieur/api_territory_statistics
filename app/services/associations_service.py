"""
Vie associative — Répertoire national des associations (RNA, ministère de l'Intérieur, export Waldec du 1er octobre
2026), table associations_by_territory (scripts/import_associations_by_territory.py).

Associations rattachées à la commune de leur siège :
  - stock au 1er octobre 2026 (year = STOCK_YEAR) : associations en activité, pour 1 000 habitants (population du
    recensement 2023), et répartition par grande catégorie (premier objet social déclaré) ;
  - créations d'associations par année (2010-2025), pour 1 000 habitants, et moyenne des cinq dernières années.
Alsace-Moselle (57, 67, 68) : associations de droit local absentes du RNA, rien n'est publié ; la région Grand Est et
la France métropolitaine sont calculées sans ces départements (associations et population).
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import AssociationsByTerritory, PopulationByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct

STOCK_YEAR = 2026
POPULATION_YEAR = 2023
LOCAL_LAW = ["57", "67", "68"]
THEMES = {
    "theme_sport": "Sport",
    "theme_culture": "Culture, pratiques artistiques, patrimoine",
    "theme_leisure": "Loisirs, comités des fêtes, animation socio-culturelle, chasse et pêche",
    "theme_social": "Action sociale, santé, solidarité, humanitaire",
    "theme_education": "Éducation, formation, recherche",
    "theme_friendly": "Amicales, entraide, anciens combattants",
    "theme_civic": "Citoyenneté, droits, information, logement, sécurité",
    "theme_environment": "Environnement, cadre de vie",
    "theme_economy": "Économie, emploi, développement local",
    "theme_religion": "Religion, spiritualité",
    "theme_other": "Autres ou non classées",
}
SOURCE = ("Ministère de l'Intérieur, Répertoire national des associations (RNA), export Waldec du 1er octobre 2026 ; "
          "associations rattachées à la commune de leur siège ; Insee, recensement 2023")


def per_1000(value, pop):
    if value is None or not pop:
        return None
    return round(value / pop * 1000, 2)


class AssociationsService(TerritoryStatsService):
    MODEL = AssociationsByTerritory
    DATA_KEY = "associations_data"
    LABEL = "associations"
    EXTRA = {"themes": THEMES, "source": SOURCE, "stock_year": STOCK_YEAR, "population_year": POPULATION_YEAR}

    def year_data(self, row):
        d = {"created": num(row.created)}
        if row.year == STOCK_YEAR:
            d["active"] = num(row.active)
            for t in THEMES:
                d[t] = num(getattr(row, t))
                d[t.replace("theme_", "share_")] = pct(d[t], d["active"])
        return d

    def _population(self, level, code):
        db = SessionLocal()
        try:
            def pop(lv, cd):
                r = (db.query(PopulationByTerritory.pop)
                     .filter(PopulationByTerritory.geo_level == lv, PopulationByTerritory.geo_code == cd,
                             PopulationByTerritory.year == POPULATION_YEAR).first())
                return num(r[0]) if r else None
            p = pop(level, str(code))
            if p is not None and (level == "FRANCE" or (level == "REG" and str(code) == "44")):
                p -= sum(pop("DEP", d) or 0 for d in LOCAL_LAW)
            return p
        except SQLAlchemyError:
            return None
        finally:
            db.close()

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        data = result[self.DATA_KEY]
        pop = self._population(level, code)
        for y, d in data.items():
            d["created_per_1000"] = per_1000(d.get("created"), pop)
        stock = data.setdefault(STOCK_YEAR, {"created": None, "active": 0.0})
        stock["population"] = pop
        stock["active_per_1000"] = per_1000(stock.get("active"), pop)
        years = sorted(y for y in data if y != STOCK_YEAR and data[y].get("created") is not None)
        last5 = years[-5:]
        avg = round(sum(data[y]["created"] for y in last5) / len(last5), 1) if last5 else None
        result["creation_years"] = years
        result["creations_avg_5y"] = {"period": f"{last5[0]}-{last5[-1]}" if last5 else None, "value": avg,
                                      "per_1000": per_1000(avg, pop)}
        result["latest_year"] = result["comparison_year"] = STOCK_YEAR
        result["evolution"] = {}
        return result
