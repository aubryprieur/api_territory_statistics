"""
Demandeurs d'emploi inscrits à France Travail — Dares, données communales trimestrielles brutes (4e trimestre,
moyenne trimestrielle, effectifs arrondis à 5), table job_seekers_by_territory (scripts/import_job_seekers_by_territory.py).

Indicateurs pour l'analyse des besoins sociaux :
  - demandeurs en catégories A, B, C (tenus de rechercher un emploi, avec ou sans activité réduite) et évolution
    en base 100 au premier millésime (2015)
  - demandeurs pour 100 actifs de 15-64 ans du recensement, aux années de recensement disponibles (2017, 2023)
  - profil : part des femmes, des moins de 25 ans, des 50 ans ou plus

Les parts sont calculées sur la somme des composantes (sexe ou âge) : les arrondis à 5 de la Dares font que leur
somme peut différer légèrement du total.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import EmploymentByTerritory, JobSeekersByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

FIELDS = ["abc", "abc_women", "abc_men", "abc_lt25", "abc_25_49", "abc_ge50"]
SOURCE = ("Dares, France Travail — demandeurs d'emploi inscrits en fin de mois, catégories A, B, C, "
          "moyenne du 4e trimestre, données brutes arrondies à 5")


class JobSeekersService(TerritoryStatsService):
    MODEL = JobSeekersByTerritory
    DATA_KEY = "job_seekers_data"
    LABEL = "demandeurs d'emploi"
    EXTRA = {"source": SOURCE}
    EVOLUTION_METRICS = ["abc", "abc_index", "women_share", "lt25_share", "ge50_share", "abc_per_100_active"]

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in FIELDS}
        d = dict(c)
        sexes = total(c["abc_women"], c["abc_men"])
        ages = total(c["abc_lt25"], c["abc_25_49"], c["abc_ge50"])
        d["women_share"] = pct(c["abc_women"], sexes)
        d["lt25_share"] = pct(c["abc_lt25"], ages)
        d["age_25_49_share"] = pct(c["abc_25_49"], ages)
        d["ge50_share"] = pct(c["abc_ge50"], ages)
        return d

    def _active(self, level, code):
        """Actifs de 15-64 ans du recensement, par année (2012, 2017, 2023)."""
        db = SessionLocal()
        try:
            rows = (db.query(EmploymentByTerritory.year, EmploymentByTerritory.active_15_64)
                    .filter(EmploymentByTerritory.geo_level == level, EmploymentByTerritory.geo_code == str(code)).all())
            return {y: num(a) for y, a in rows}
        except SQLAlchemyError:
            return {}
        finally:
            db.close()

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        data = result[self.DATA_KEY]
        years = sorted(data)
        base = data[years[0]].get("abc")
        active = self._active(level, code)
        for y in years:
            d = data[y]
            d["abc_index"] = round(d["abc"] / base * 100, 1) if d.get("abc") is not None and base else None
            d["active_15_64"] = active.get(y)
            d["abc_per_100_active"] = pct(d.get("abc"), active.get(y))
        result["base_year"] = years[0]
        result["census_years"] = [y for y in years if data[y]["abc_per_100_active"] is not None]
        result["evolution"] = self.evolution(data, start_year, end_year)
        return result
