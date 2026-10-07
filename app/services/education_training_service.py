"""
Scolarisation et diplômes — INSEE, recensement (DS_RP_EDUCATION_PRINC, DS_RP_DIPLOMES_PRINC),
table education_by_territory. Millésimes 2012, 2017, 2023 ; valeurs officielles par territoire.

Taux de scolarisation : population scolarisée / population de la tranche d'âge.
Diplômes : part de la population de 15 ans ou plus NON scolarisée, selon le diplôme le plus élevé.
"""
from app.models import EducationByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

AGES = ["2_5", "6_10", "11_14", "15_17", "18_24", "25_29", "30_plus"]
AGE_LABELS = {"2_5": "2-5 ans", "6_10": "6-10 ans", "11_14": "11-14 ans", "15_17": "15-17 ans",
              "18_24": "18-24 ans", "25_29": "25-29 ans", "30_plus": "30 ans ou plus"}
DIPLOMA_LEVELS = ["no_diploma", "bepc", "cap_bep", "bac", "higher_education",
                  "bac2", "bac3_4", "bac5_plus", "bac3_plus"]
DIPLOMA_LABELS = {
    "no_diploma": "Aucun diplôme ou certificat d'études primaires",
    "bepc": "BEPC, brevet des collèges, DNB",
    "cap_bep": "CAP, BEP ou équivalent",
    "bac": "Baccalauréat, brevet professionnel ou équivalent",
    "higher_education": "Diplôme de l'enseignement supérieur",
    "bac2": "Bac + 2",
    "bac3_4": "Bac + 3 ou 4",
    "bac5_plus": "Bac + 5 ou plus",
    "bac3_plus": "Bac + 3 ou plus",
}

COUNT_FIELDS = (
    [f"{p}_{a}" for a in AGES for p in ("pop", "enrolled")]
    + [f"{p}_{a}_{s}" for a in ("15_17", "18_24") for s in ("men", "women") for p in ("pop", "enrolled")]
    + ["non_enrolled_15_plus"] + DIPLOMA_LEVELS
    + [f"{f}_{s}" for s in ("men", "women") for f in ("non_enrolled_15_plus", "no_diploma", "higher_education")]
)


class EducationTrainingService(TerritoryStatsService):
    MODEL = EducationByTerritory
    DATA_KEY = "education_data"
    LABEL = "scolarisation et diplômes"
    EXTRA = {"labels": {"ages": AGE_LABELS, "diplomas": DIPLOMA_LABELS}}
    EVOLUTION_METRICS = (
        [f"schooling_rate_{a}" for a in AGES]
        + ["schooling_rate_15_17_men", "schooling_rate_15_17_women",
           "schooling_rate_18_24_men", "schooling_rate_18_24_women", "not_enrolled_18_24"]
        + [f"{lvl}_percentage" for lvl in DIPLOMA_LEVELS]
        + ["low_qualification_percentage", "no_diploma_percentage_men", "no_diploma_percentage_women",
           "higher_education_percentage_men", "higher_education_percentage_women"]
    )

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in COUNT_FIELDS}
        d = dict(c)

        # --- Scolarisation (% de la tranche d'âge)
        for a in AGES:
            d[f"schooling_rate_{a}"] = pct(c[f"enrolled_{a}"], c[f"pop_{a}"])
        for a in ("15_17", "18_24"):
            for s in ("men", "women"):
                d[f"schooling_rate_{a}_{s}"] = pct(c[f"enrolled_{a}_{s}"], c[f"pop_{a}_{s}"])
        d["not_enrolled_15_17"] = (c["pop_15_17"] - c["enrolled_15_17"]
                                   if c["pop_15_17"] is not None and c["enrolled_15_17"] is not None else None)
        d["not_enrolled_18_24"] = (c["pop_18_24"] - c["enrolled_18_24"]
                                   if c["pop_18_24"] is not None and c["enrolled_18_24"] is not None else None)

        # --- Diplômes (% de la population de 15 ans ou plus non scolarisée)
        base = c["non_enrolled_15_plus"]
        for lvl in DIPLOMA_LEVELS:
            d[f"{lvl}_percentage"] = pct(c[lvl], base)
        d["low_qualification"] = total(c["no_diploma"], c["bepc"])  # au plus le brevet
        d["low_qualification_percentage"] = pct(d["low_qualification"], base)
        for s in ("men", "women"):
            d[f"no_diploma_percentage_{s}"] = pct(c[f"no_diploma_{s}"], c[f"non_enrolled_15_plus_{s}"])
            d[f"higher_education_percentage_{s}"] = pct(c[f"higher_education_{s}"], c[f"non_enrolled_15_plus_{s}"])
        return d
