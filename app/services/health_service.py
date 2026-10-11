"""
Santé — trois services sur les tables de scripts/import_health_by_territory.py :

  HealthProfessionalsService  densité de professionnels de santé libéraux pour 100 000 habitants (Observatoire des
                              territoires — ANCT ; RPPS, Adeli, BPE 2025, recensement 2023). Pédiatres : pour 100 000
                              enfants de moins de 15 ans ; gynécologues et sages-femmes : pour 100 000 femmes de 15 ans
                              ou plus. France métropolitaine : moyenne des régions pondérée par la population.
  HealthInsuranceService      bénéficiaires du régime général de l'assurance maladie et de la complémentaire santé
                              solidaire (C2S) au 1er janvier (Cnam, diffusion Insee). Seules les communes découpées en
                              IRIS sont publiées ; EPCI, département, région et France = ensemble de ces communes.
  AldService                  affections de longue durée (régime général) : taux standardisés pour 100 000 personnes
                              protégées par département ; France entière : prévalence nationale.
"""
from app.models import AldByTerritory, HealthInsuranceByTerritory, HealthProfessionalsByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

PROFESSIONS = {
    "gp": "Médecins généralistes", "nurse": "Infirmiers", "physio": "Masseurs-kinésithérapeutes",
    "dentist": "Chirurgiens-dentistes", "midwife": "Sages-femmes", "psychologist": "Psychologues",
    "pediatrician": "Pédiatres", "gynecologist": "Gynécologues", "psychiatrist": "Psychiatres",
    "ophthalmologist": "Ophtalmologues", "cardiologist": "Cardiologues", "dermatologist": "Dermatologues",
    "gastroenterologist": "Gastro-entérologues", "pulmonologist": "Pneumologues", "ent": "ORL",
    "radiologist": "Radiologues",
}
PRIMARY_CARE = ["gp", "nurse", "physio", "dentist", "midwife", "psychologist"]
DENOMINATORS = {"pediatrician": "enfants de moins de 15 ans", "gynecologist": "femmes de 15 ans ou plus",
                "midwife": "femmes de 15 ans ou plus"}

INSURANCE_FIELDS = ["insured", "insured_men", "insured_women", "insured_lt18", "insured_18_24", "insured_25_49",
                    "insured_50_59", "insured_60_74", "insured_ge75", "c2s_free", "c2s_free_lt18", "c2s_free_18_24",
                    "c2s_free_25_49", "c2s_free_50_59", "c2s_free_ge60", "c2s_free_men", "c2s_free_women",
                    "c2s_paid", "c2s_paid_lt18", "c2s_paid_ge60", "communes"]

ALD = {"diabetes": "Diabète", "cancer": "Tumeurs malignes (cancers)", "psychiatric": "Affections psychiatriques de longue durée",
       "heart_failure": "Insuffisance cardiaque, troubles du rythme, cardiopathies graves", "coronary": "Maladie coronaire",
       "stroke": "Accident vasculaire cérébral invalidant", "respiratory": "Insuffisance respiratoire chronique grave",
       "alzheimer": "Maladie d'Alzheimer et autres démences", "parkinson": "Maladie de Parkinson"}


class HealthProfessionalsService(TerritoryStatsService):
    MODEL = HealthProfessionalsByTerritory
    DATA_KEY = "health_professionals_data"
    LABEL = "professionnels de santé"
    EXTRA = {"professions": PROFESSIONS, "primary_care": PRIMARY_CARE, "denominators": DENOMINATORS,
             "source": "Observatoire des territoires (ANCT) — RPPS, Adeli ; Insee, BPE 2025 et recensement 2023"}

    def year_data(self, row):
        return {f"{k}_density": num(getattr(row, f"{k}_density")) for k in PROFESSIONS}


class HealthInsuranceService(TerritoryStatsService):
    MODEL = HealthInsuranceByTerritory
    DATA_KEY = "health_insurance_data"
    LABEL = "complémentaire santé solidaire"
    EXTRA = {"source": "Cnam, bénéficiaires du régime général au 1er janvier (diffusion Insee, données au niveau Iris)",
             "scope": "communes découpées en IRIS"}
    EVOLUTION_METRICS = ["c2s_free_rate", "c2s_paid_rate", "c2s_rate"]

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in INSURANCE_FIELDS}
        d = dict(c)
        d["c2s_free_rate"] = pct(c["c2s_free"], c["insured"])            # C2S sans participation (ex-CMU-C)
        d["c2s_paid_rate"] = pct(c["c2s_paid"], c["insured"])            # C2S avec participation (ex-ACS)
        d["c2s_rate"] = pct(total(c["c2s_free"], c["c2s_paid"]), c["insured"])
        d["c2s_free_lt18_rate"] = pct(c["c2s_free_lt18"], c["insured_lt18"])
        d["c2s_free_18_24_rate"] = pct(c["c2s_free_18_24"], c["insured_18_24"])
        d["c2s_free_25_49_rate"] = pct(c["c2s_free_25_49"], c["insured_25_49"])
        d["c2s_free_50_59_rate"] = pct(c["c2s_free_50_59"], c["insured_50_59"])
        d["c2s_free_ge60_rate"] = pct(c["c2s_free_ge60"], total(c["insured_60_74"], c["insured_ge75"]))
        d["c2s_free_women_share"] = pct(c["c2s_free_women"], total(c["c2s_free_women"], c["c2s_free_men"]))
        return d

    def default_period(self, years):
        return years[0], years[-1]   # deux éditions (2022, 2025)


class AldService(TerritoryStatsService):
    MODEL = AldByTerritory
    DATA_KEY = "ald_data"
    LABEL = "affections de longue durée"
    EXTRA = {"affections": ALD,
             "source": "Cnam, personnes prises en charge pour affection de longue durée, régime général ; taux "
                       "standardisés sur l'âge et le sexe pour 100 000 personnes protégées (France entière : prévalence)"}

    def year_data(self, row):
        d = {}
        for k in ALD:
            d[f"{k}_count"] = num(getattr(row, f"{k}_count"))
            d[f"{k}_rate"] = num(getattr(row, f"{k}_rate"))
        return d

    def france(self, start_year=None, end_year=None):
        return self.get("FRANCE", "FE", start_year, end_year)   # France entière
