"""
Immigrés et étrangers — INSEE, recensement 2023, table immigration_by_territory.

Un immigré est né étranger à l'étranger (il peut être devenu français) ; un étranger n'a pas la nationalité
française (il peut être né en France). Taux calculés pour l'analyse des besoins sociaux :
  - part des immigrés et des étrangers dans la population, part des femmes parmi les immigrés
  - âge : part des 55 ans ou plus parmi les immigrés, part des immigrés parmi les 55 ans ou plus,
    part d'étrangers parmi les moins de 15 ans
  - emploi : taux de chômage (15 ans ou plus) des immigrés / non-immigrés et des étrangers / Français,
    taux d'emploi des 25-54 ans, des femmes de 25-54 ans, part des femmes de 25-54 ans au foyer
  - catégorie socioprofessionnelle : part des ouvriers et employés (15 ans ou plus ayant une profession)
Un seul millésime (2023) : pas d'évolution.
"""
from app.models import ImmigrationByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

GROUPS = ("imm", "nonimm")
ACTIVITY = ("employed", "unemployed", "retired", "students", "homemakers", "other_inactive")


class ImmigrationService(TerritoryStatsService):
    MODEL = ImmigrationByTerritory
    DATA_KEY = "immigration_data"
    LABEL = "immigrés et étrangers"
    EXTRA = {"source": "INSEE, recensement de la population 2023 (exploitations principale et complémentaire)"}
    EVOLUTION_METRICS = []

    def year_data(self, row):
        d = {c: num(getattr(row, c)) for c in ImmigrationByTerritory.__table__.columns.keys()
             if c not in ("geo_level", "geo_code", "year")}
        pop = d["population"]
        d["immigrant_rate"] = pct(d["imm"], pop)
        d["foreigner_rate"] = pct(d["foreign"], pop)
        d["immigrant_women_share"] = pct(d["imm_women"], d["imm"])
        d["foreign_lt15_rate"] = pct(d["foreign_lt15"], total(d["foreign_lt15"], d["french_lt15"]))
        d["immigrant_share_ge55"] = pct(d["imm_ge55"], total(d["imm_ge55"], d["nonimm_ge55"]))
        for g in GROUPS:
            d[f"{g}_ge55_share"] = pct(d[f"{g}_ge55"], d[g])
            d[f"{g}_unemployment_rate"] = pct(d[f"{g}_unemployed_15p"],
                                              total(d[f"{g}_employed_15p"], d[f"{g}_unemployed_15p"]))
            d[f"{g}_employment_rate_25_54"] = pct(d[f"{g}_employed_25_54"], d[f"{g}_25_54"])
            d[f"{g}_women_employment_rate_25_54"] = pct(d[f"{g}_women_employed_25_54"], d[f"{g}_women_25_54"])
            d[f"{g}_women_homemakers_rate_25_54"] = pct(d[f"{g}_women_homemakers_25_54"], d[f"{g}_women_25_54"])
            pcs = total(*[d[f"{g}_pcs{i}"] for i in "123456"])
            d[f"{g}_workers_employees_share"] = pct(total(d[f"{g}_pcs5"], d[f"{g}_pcs6"]), pcs)
        for g in ("foreign", "french"):
            d[f"{g}_unemployment_rate"] = pct(d[f"{g}_unemployed_15p"],
                                              total(d[f"{g}_employed_15p"], d[f"{g}_unemployed_15p"]))
        return d
