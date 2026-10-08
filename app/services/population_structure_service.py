"""
Population — INSEE, recensement. Deux tables, valeurs officielles par territoire :
  - population_by_territory (2012, 2017, 2023) : structure par âge et sexe, pyramide des âges (2023),
    catégories socioprofessionnelles des 15 ans ou plus, mobilité résidentielle (lieu de résidence 1 an avant)
  - population_history_by_territory (1968 → 2023) : population, naissances et décès entre recensements,
    logements, superficie

Indicateurs pour l'analyse des besoins sociaux :
  - structure par âge : jeunes, seniors, grand âge ; indice de vieillissement ; rapport de dépendance
  - pyramide des âges par tranche de 5 ans et sexe (2023) ; tranches de l'enfance et de la jeunesse
  - catégories socioprofessionnelles des 15 ans ou plus (dont retraités)
  - mobilité résidentielle : nouveaux arrivants, origine, âge des arrivants
  - évolution longue (1968 → 2023) : taux de variation annuel, part due au solde naturel et au solde migratoire
"""
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import PopulationByTerritory, PopulationHistoryByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

AGES = {"lt15": "Moins de 15 ans", "15_24": "15-24 ans", "25_39": "25-39 ans", "40_54": "40-54 ans",
        "55_64": "55-64 ans", "65_79": "65-79 ans", "ge80": "80 ans ou plus"}
AGE_AGGREGATES = ["ge65", "lt20", "20_64"]
SEXES = ["", "_women", "_men"]
PCS = {"1": "Agriculteurs exploitants", "2": "Artisans, commerçants, chefs d'entreprise",
       "3": "Cadres et professions intellectuelles supérieures", "4": "Professions intermédiaires",
       "5": "Employés", "6": "Ouvriers", "7": "Retraités", "9": "Autres personnes sans activité professionnelle"}
MOBILITY = {"same_dwelling": "Même logement", "same_commune": "Autre logement de la même commune",
            "same_department": "Autre commune du département", "same_region": "Autre département de la région",
            "other_region": "Autre région de France métropolitaine", "overseas": "Outre-mer",
            "abroad": "Étranger"}
NEWCOMER_AGES = {"1_14": "1-14 ans", "15_24": "15-24 ans", "25_54": "25-54 ans", "ge55": "55 ans ou plus"}
PYRAMID_GROUPS = [f"{a}_{a + 4}" for a in range(0, 95, 5)] + ["ge95"]
PYRAMID_LABELS = {g: ("95 ans ou +" if g == "ge95" else g.replace("_", "-") + " ans") for g in PYRAMID_GROUPS}
CHILDHOOD = {"0_2": "0-2 ans", "3_5": "3-5 ans", "6_10": "6-10 ans", "11_14": "11-14 ans",
             "15_17": "15-17 ans", "18_24": "18-24 ans"}

COUNT_FIELDS = (
    [f"pop{'_' + a if a else ''}{s}" for a in [""] + list(AGES) + AGE_AGGREGATES for s in SEXES]
    + ["pop_15p"] + [f"pcs_{p}" for p in PCS]
    + ["mig_total", "mig_other_commune"] + [f"mig_{k}" for k in MOBILITY]
    + [f"mig_other_commune_{a}" for a in NEWCOMER_AGES]
    + [f"pyr_{s}_{g}" for s in ("men", "women") for g in PYRAMID_GROUPS]
    + [f"age_{k}" for k in CHILDHOOD]
)

# Dates de référence des recensements (durée exacte des périodes intercensitaires)
CENSUS_DATES = {1968: date(1968, 3, 1), 1975: date(1975, 2, 20), 1982: date(1982, 3, 4), 1990: date(1990, 3, 5),
                1999: date(1999, 3, 8)}


def _census_date(year):
    return CENSUS_DATES.get(year, date(year, 1, 1))  # depuis 2004 : population au 1er janvier


def _ratio(a, b, factor=100, digits=1):
    return round(a / b * factor, digits) if a is not None and b else None


class PopulationStructureService(TerritoryStatsService):
    MODEL = PopulationByTerritory
    DATA_KEY = "population_data"
    LABEL = "population"
    EXTRA = {"labels": {"ages": AGES, "pcs": PCS, "mobility": MOBILITY, "newcomer_ages": NEWCOMER_AGES,
                        "pyramid": PYRAMID_LABELS, "childhood": CHILDHOOD}}
    EVOLUTION_METRICS = (
        ["pop", "women_percentage"]
        + [f"age_{a}_percentage" for a in list(AGES) + AGE_AGGREGATES]
        + ["aging_index", "dependency_ratio"]
        + [f"pcs_{p}_percentage" for p in PCS] + ["working_class_percentage"]
        + ["newcomers_percentage", "moved_within_commune_percentage", "same_dwelling_percentage",
           "from_abroad_percentage"]
    )

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in COUNT_FIELDS}
        d = dict(c)
        pop = c["pop"]

        # --- Structure par âge et sexe (% de la population)
        d["women_percentage"] = pct(c["pop_women"], pop)
        for a in list(AGES) + AGE_AGGREGATES:
            for s in SEXES:
                d[f"age_{a}_percentage{s}"] = pct(c[f"pop_{a}{s}"], c[f"pop{s}"])
        d["aging_index"] = _ratio(c["pop_ge65"], c["pop_lt20"])                     # 65 ans ou + pour 100 < 20 ans
        d["dependency_ratio"] = _ratio(total(c["pop_lt20"], c["pop_ge65"]), c["pop_20_64"])  # pour 100 20-64 ans
        d["women_ge80_percentage"] = pct(c["pop_ge80_women"], c["pop_ge80"])         # féminisation du grand âge

        # --- Pyramide des âges (2023) et tranches de l'enfance / jeunesse (% de la population)
        for s in ("men", "women"):
            for g in PYRAMID_GROUPS:
                d[f"pyr_{s}_{g}_percentage"] = pct(c[f"pyr_{s}_{g}"], pop)
        for k in CHILDHOOD:
            d[f"age_{k}_percentage"] = pct(c[f"age_{k}"], pop)

        # --- Catégories socioprofessionnelles (% des 15 ans ou plus)
        for p in PCS:
            d[f"pcs_{p}_percentage"] = pct(c[f"pcs_{p}"], c["pop_15p"])
        d["working_class_percentage"] = pct(total(c["pcs_5"], c["pcs_6"]), c["pop_15p"])  # employés + ouvriers

        # --- Mobilité résidentielle (% des habitants d'un an ou plus)
        mig = c["mig_total"]
        for k in MOBILITY:
            d[f"mobility_{k}_percentage"] = pct(c[f"mig_{k}"], mig)
        d["same_dwelling_percentage"] = d["mobility_same_dwelling_percentage"]
        d["moved_within_commune_percentage"] = d["mobility_same_commune_percentage"]
        d["newcomers_percentage"] = pct(c["mig_other_commune"], mig)   # arrivés d'une autre commune (ou de l'étranger)
        d["from_abroad_percentage"] = d["mobility_abroad_percentage"]
        for a in NEWCOMER_AGES:   # répartition des nouveaux arrivants par âge
            d[f"newcomers_{a}_percentage"] = pct(c[f"mig_other_commune_{a}"], c["mig_other_commune"])
        return d

    # ------------------------------------------------------------- série longue
    def history(self, level, code):
        db = SessionLocal()
        try:
            rows = (db.query(PopulationHistoryByTerritory)
                    .filter(PopulationHistoryByTerritory.geo_level == level,
                            PopulationHistoryByTerritory.geo_code == str(code))
                    .order_by(PopulationHistoryByTerritory.year).all())
        except SQLAlchemyError:
            return {}
        finally:
            db.close()
        if not rows:
            return {}

        area = next((num(r.area_km2) for r in reversed(rows) if num(r.area_km2)), None)
        first = num(rows[0].population)
        censuses = []
        for r in rows:
            p, main = num(r.population), num(r.dwellings_main)
            censuses.append({
                "year": r.year,
                "population": p,
                "index_base_100": _ratio(p, first, 100, 1),           # base 100 au premier recensement (1968)
                "density": round(p / area, 1) if p is not None and area else None,  # hab./km² (superficie 2023)
                "dwellings": num(r.dwellings),
                "dwellings_main": main,
                "vacancy_rate": pct(num(r.dwellings_vacant), num(r.dwellings)),
                "persons_per_dwelling": _ratio(num(r.households_population), main, 1, 2),
            })

        periods = []
        for prev, cur in zip(rows, rows[1:]):
            p0, p1 = num(prev.population), num(cur.population)
            births, deaths = num(cur.births), num(cur.deaths)
            years = (_census_date(cur.year) - _census_date(prev.year)).days / 365.25
            entry = {"period": f"{prev.year}-{cur.year}", "start_year": prev.year, "end_year": cur.year,
                     "years": round(years, 2), "population_change": None, "annual_growth_rate": None,
                     "natural_balance": None, "migration_balance": None, "annual_natural_rate": None,
                     "annual_migration_rate": None, "birth_rate": None, "death_rate": None}
            if p0 and p1:
                change = p1 - p0
                tvam = ((p1 / p0) ** (1 / years) - 1) * 100            # taux de variation annuel moyen (%)
                mean_pop = (p0 + p1) / 2
                entry.update(population_change=round(change), annual_growth_rate=round(tvam, 2))
                if births is not None and deaths is not None:
                    natural = births - deaths
                    nat_rate = natural / (mean_pop * years) * 100     # part due au solde naturel (convention INSEE)
                    entry.update(
                        natural_balance=round(natural),
                        migration_balance=round(change - natural),    # solde migratoire apparent
                        annual_natural_rate=round(nat_rate, 2),
                        annual_migration_rate=round(tvam - nat_rate, 2),
                        birth_rate=round(births / (mean_pop * years) * 1000, 1),   # ‰ par an
                        death_rate=round(deaths / (mean_pop * years) * 1000, 1),
                    )
            periods.append(entry)
        return {"area_km2": area, "censuses": censuses, "periods": periods}

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" not in result:
            result["history"] = self.history(level, str(code))
        return result
