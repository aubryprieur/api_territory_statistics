"""
Ménages — données INSEE du recensement (DS_RP_MENAGES_COMP et DS_RP_MENAGES_PRINC),
table households_by_territory.

Les effectifs sont les valeurs officielles INSEE à chaque échelle (commune, EPCI,
département, région, France métropolitaine) : aucune agrégation n'est faite ici.
Seuls les taux sont calculés, à partir des effectifs de la même ligne.

Millésimes disponibles : 2012, 2017, 2023. Par défaut, l'évolution compare le dernier
millésime au millésime situé 5 à 6 ans plus tôt (2017 -> 2023).
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import HouseholdByTerritory
from app.services.family_service import FRANCE_CODE, MIN_EVOLUTION_GAP, _num, _pct

AGES = ["15_24", "25_39", "40_54", "55_64", "65_79", "80_plus"]
AGE_LABELS = {"15_24": "15-24 ans", "25_39": "25-39 ans", "40_54": "40-54 ans",
              "55_64": "55-64 ans", "65_79": "65-79 ans", "80_plus": "80 ans ou plus"}

HOUSEHOLD_TYPES = ["one_person", "men_alone", "women_alone", "other_without_family", "with_family",
                   "single_parent", "couple_without_children", "couple_with_children"]

PCS = {
    "1": "Agriculteurs exploitants",
    "2": "Artisans, commerçants, chefs d'entreprise",
    "3": "Cadres et professions intellectuelles supérieures",
    "4": "Professions intermédiaires",
    "5": "Employés",
    "6": "Ouvriers",
    "7": "Retraités",
    "9": "Autres personnes sans activité professionnelle",
}

COUNT_FIELDS = (["households", "household_population"] + HOUSEHOLD_TYPES + [f"pcs_{c}" for c in PCS]
                + [f"living_alone_{a}" for a in AGES] + [f"household_population_{a}" for a in AGES])

EVOLUTION_METRICS = (
    ["households", "household_population", "average_household_size"]
    + [f"{t}_percentage" for t in HOUSEHOLD_TYPES]
    + [f"pcs_{c}_percentage" for c in PCS]
    + ["living_alone", "living_alone_rate_15_plus", "living_alone_rate_65_plus"]
    + [f"living_alone_rate_{a}" for a in AGES]
)


def _sum(values):
    values = [v for v in values if v is not None]
    return sum(values) if values else None


class HouseholdService:

    def _year_data(self, row):
        c = {f: _num(getattr(row, f)) for f in COUNT_FIELDS}
        households = c["households"]
        data = dict(c)

        # Taille moyenne des ménages
        data["average_household_size"] = (
            round(c["household_population"] / households, 2)
            if households and c["household_population"] is not None else None
        )
        # Composition des ménages (% des ménages)
        for t in HOUSEHOLD_TYPES:
            data[f"{t}_percentage"] = _pct(c[t], households)
        # Ménages selon la PCS de la personne de référence (% des ménages)
        for code in PCS:
            data[f"pcs_{code}_percentage"] = _pct(c[f"pcs_{code}"], households)

        # Personnes vivant seules (% de la population des ménages de chaque âge)
        for a in AGES:
            data[f"living_alone_rate_{a}"] = _pct(c[f"living_alone_{a}"], c[f"household_population_{a}"])
        alone_15 = _sum(c[f"living_alone_{a}"] for a in AGES)
        pop_15 = _sum(c[f"household_population_{a}"] for a in AGES)
        alone_65 = _sum([c["living_alone_65_79"], c["living_alone_80_plus"]])
        pop_65 = _sum([c["household_population_65_79"], c["household_population_80_plus"]])
        data["living_alone"] = alone_15
        data["living_alone_65_plus"] = alone_65
        data["living_alone_rate_15_plus"] = _pct(alone_15, pop_15)
        data["living_alone_rate_65_plus"] = _pct(alone_65, pop_65)
        return data

    def _default_period(self, years):
        end = years[-1]
        earlier = [y for y in years if y <= end - MIN_EVOLUTION_GAP]
        return (earlier[-1] if earlier else years[0]), end

    def _calculate_evolution(self, data, start_year, end_year):
        years = sorted(data)
        if len(years) < 2:
            return {}
        default_start, default_end = self._default_period(years)
        start_year = start_year or default_start
        end_year = end_year or default_end
        if start_year not in data or end_year not in data:
            return {"error": f"Millésimes disponibles : {', '.join(map(str, years))}"}
        evolutions = {}
        for metric in EVOLUTION_METRICS:
            v0, v1 = data[start_year].get(metric), data[end_year].get(metric)
            if v0 is None or v1 is None:
                continue
            evolutions[metric] = {
                "start_value": v0,
                "end_value": v1,
                "difference": round(v1 - v0, 2),  # en points pour les taux
                "evolution_percentage": round((v1 - v0) / v0 * 100, 2) if v0 else 0.0,
                "period": f"{start_year}-{end_year}",
            }
        return evolutions

    def _get(self, level, code, start_year=None, end_year=None):
        db = SessionLocal()
        try:
            rows = (
                db.query(HouseholdByTerritory)
                .filter(HouseholdByTerritory.geo_level == level, HouseholdByTerritory.geo_code == str(code))
                .order_by(HouseholdByTerritory.year)
                .all()
            )
            if not rows:
                return {"error": f"Aucune donnée ménages pour {level} {code}"}
            data = {row.year: self._year_data(row) for row in rows}
            start, end = self._default_period(sorted(data))
            return {
                "territory": {"level": level, "code": str(code)},
                "available_years": sorted(data),
                "latest_year": end,
                "comparison_year": start,
                "labels": {"pcs": PCS, "ages": AGE_LABELS},
                "household_data": data,
                "evolution": self._calculate_evolution(data, start_year, end_year),
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def get_households_by_commune(self, code: str, start_year: int = None, end_year: int = None):
        code = str(code).zfill(5)
        result = self._get("COM", code, start_year, end_year)
        if "error" in result:
            arm = self._get("ARM", code, start_year, end_year)  # arrondissements Paris/Lyon/Marseille
            if "error" not in arm:
                return arm
        return result

    def get_households_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        return self._get("EPCI", epci, start_year, end_year)

    def get_households_by_department(self, dep: str, start_year: int = None, end_year: int = None):
        dep = str(dep)
        if dep.isdigit() and len(dep) < 2:
            dep = dep.zfill(2)
        return self._get("DEP", dep, start_year, end_year)

    def get_households_by_region(self, reg: str, start_year: int = None, end_year: int = None):
        return self._get("REG", str(reg).zfill(2), start_year, end_year)

    def get_households_france(self, start_year: int = None, end_year: int = None):
        """France métropolitaine."""
        return self._get("FRANCE", FRANCE_CODE, start_year, end_year)
