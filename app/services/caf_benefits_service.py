"""
Prestations CAF — Cnaf (data.caf.fr), table caf_benefits_by_territory, au 31 décembre 2020 à 2024.

Effectifs publiés par la Cnaf (foyers allocataires, personnes couvertes, montants mensuels) et taux
pour l'analyse des besoins sociaux, rapportés aux données du recensement 2023 du même territoire
(households_by_territory, population_by_territory, families_by_territory) :
  - part des ménages allocataires de la CAF, part de la population couverte
  - RSA, prime d'activité : part des ménages allocataires, part de la population couverte
  - aides au logement : part des ménages, répartition APL / ALF / ALS
  - AAH (bénéficiaires pour 100 personnes de 20 à 64 ans), AEEH — hors communes (non publiées)
  - familles : allocations familiales, allocation de soutien familial (familles monoparentales), Paje
  - montants mensuels moyens par foyer
Les dénominateurs du recensement 2023 sont appliqués à toutes les années : les taux 2020-2022 et
2024 sont donc approchés (la population évolue peu sur la période).
"""
from app.database import SessionLocal
from app.models import (CafBenefitsByTerritory, FamilyByTerritory, HouseholdByTerritory,
                        PopulationByTerritory)
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

DENOMINATOR_YEAR = 2023
BENEFITS = {
    "all": "Ensemble des prestations",
    "rsa": "Revenu de solidarité active (RSA)",
    "ppa": "Prime d'activité",
    "insertion": "RSA et prime d'activité",
    "housing": "Aides au logement",
    "apl": "Aide personnalisée au logement (APL)",
    "alf": "Allocation de logement familiale (ALF)",
    "als": "Allocation de logement sociale (ALS)",
    "children": "Prestations enfance et jeunesse",
    "af": "Allocations familiales",
    "cf": "Complément familial",
    "ars": "Allocation de rentrée scolaire",
    "asf": "Allocation de soutien familial (ASF)",
    "paje": "Prestation d'accueil du jeune enfant (Paje)",
    "paje_basic": "Allocation de base de la Paje",
    "cmg": "Complément de libre choix du mode de garde (CMG)",
    "prepare": "Prestation partagée d'éducation de l'enfant (PreParE)",
    "disability": "Prestations liées au handicap",
    "aah": "Allocation aux adultes handicapés (AAH)",
    "aeeh": "Allocation d'éducation de l'enfant handicapé (AEEH)",
}
MEASURES = ["households", "persons", "amount"]
COUNT_FIELDS = [f"{b}_{m}" for b in BENEFITS for m in MEASURES] + ["aah_beneficiaries", "aeeh_beneficiaries"]


def _avg(amount, households):
    return round(amount / households) if amount is not None and households else None


class CafBenefitsService(TerritoryStatsService):
    MODEL = CafBenefitsByTerritory
    DATA_KEY = "caf_data"
    LABEL = "prestations CAF"
    EXTRA = {"labels": {"benefits": BENEFITS}, "source": "Cnaf, data.caf.fr — foyers allocataires au 31 décembre",
             "denominator_year": DENOMINATOR_YEAR}
    EVOLUTION_METRICS = (
        [f"{b}_households" for b in ("all", "rsa", "ppa", "housing", "af", "asf", "paje", "cmg")]
        + ["all_persons", "rsa_persons", "aah_beneficiaries"]
        + ["households_covered_rate", "population_covered_rate", "rsa_households_rate", "rsa_population_rate",
           "ppa_households_rate", "housing_households_rate", "housing_population_rate", "aah_rate",
           "asf_single_parent_rate", "rsa_share", "ppa_share", "housing_share"]
    )

    # ------------------------------------------------------------ dénominateurs
    def denominators(self, level, code):
        """Ménages, population, familles du recensement 2023 pour le même territoire."""
        db = SessionLocal()
        try:
            def row(model):
                return (db.query(model).filter(model.geo_level == level, model.geo_code == str(code),
                                               model.year == DENOMINATOR_YEAR).first())
            hh, pop, fam = row(HouseholdByTerritory), row(PopulationByTerritory), row(FamilyByTerritory)
            families_with_children = None
            if fam is not None and num(fam.total_families) is not None and num(fam.families_0_children) is not None:
                families_with_children = num(fam.total_families) - num(fam.families_0_children)
            return {
                "households": num(hh.households) if hh else None,
                "population": num(pop.pop) if pop else None,
                "population_20_64": num(pop.pop_20_64) if pop else None,
                "children_0_2": num(pop.age_0_2) if pop else None,
                "single_parent_families": num(fam.single_parent_families) if fam else None,
                "families_with_children": families_with_children,
            }
        except Exception:
            return {}
        finally:
            db.close()

    def year_data(self, row):
        return {f: num(getattr(row, f)) for f in COUNT_FIELDS}

    @staticmethod
    def add_rates(d, den):
        hh, pop = den.get("households"), den.get("population")
        allh = d["all_households"]
        d["households_covered_rate"] = pct(allh, hh)            # ménages allocataires / ménages
        d["population_covered_rate"] = pct(d["all_persons"], pop)  # personnes couvertes / population
        for b in ("rsa", "ppa", "insertion", "housing"):
            d[f"{b}_households_rate"] = pct(d[f"{b}_households"], hh)
            d[f"{b}_population_rate"] = pct(d[f"{b}_persons"], pop)
        d["aah_rate"] = pct(d["aah_beneficiaries"], den.get("population_20_64"))   # pour 100 personnes de 20-64 ans
        d["asf_single_parent_rate"] = pct(d["asf_households"], den.get("single_parent_families"))
        d["af_families_rate"] = pct(d["af_households"], den.get("families_with_children"))
        d["cmg_children_rate"] = pct(d["cmg_households"], den.get("children_0_2"))  # ordre de grandeur
        # Poids de chaque prestation parmi les foyers allocataires
        for b in ("rsa", "ppa", "housing", "af", "asf", "paje", "aah"):
            d[f"{b}_share"] = pct(d[f"{b}_households"], allh)
        # Répartition des aides au logement
        housing_total = total(d["apl_households"], d["alf_households"], d["als_households"])
        for b in ("apl", "alf", "als"):
            d[f"{b}_housing_share"] = pct(d[f"{b}_households"], housing_total)
        # Montants mensuels moyens par foyer (euros)
        for b in ("all", "rsa", "ppa", "housing", "aah", "af"):
            d[f"{b}_average_amount"] = _avg(d[f"{b}_amount"], d[f"{b}_households"])
        return d

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        den = self.denominators(level, code)
        data = {y: self.add_rates(d, den) for y, d in result[self.DATA_KEY].items()}
        result[self.DATA_KEY] = data
        result["denominators"] = den
        result["evolution"] = self.evolution(data, start_year, end_year)
        return result
