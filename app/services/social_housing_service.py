"""
Parc locatif social — SDES, répertoire des logements locatifs des bailleurs sociaux (RPLS) au 1er janvier,
table social_housing_by_territory (scripts/import_social_housing_by_territory.py).

  - séries 2013 → 2025 : parc social, mises en service, taux de vacance (totale, > 3 mois), taux de mobilité
    (rotation), loyer moyen au m² de surface habitable
  - structure du parc au 1er janvier 2025 : densité pour 100 résidences principales, logements en QPV, individuel,
    taille, financement d'origine (PLAI = très social ; PLS, PLI = intermédiaire), âge, étiquettes énergie (DPE),
    sorties du parc (ventes, démolitions)
"""
from app.models import SocialHousingByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

FIELDS = ['social_dwellings', 'new_dwellings', 'vacancy_rate', 'vacancy_3m_rate', 'mobility_rate', 'avg_rent_m2',
          'rented', 'vacant', 'offered', 'density', 'in_qpv', 'individual', 'collective', 'rooms_1', 'rooms_2',
          'rooms_3', 'rooms_4', 'rooms_5p', 'fin_plai', 'fin_plus_after_77', 'fin_plus_before_77', 'fin_pls',
          'fin_pli', 'avg_age', 'age_lt10', 'age_ge60', 'sold', 'demolished', 'dpe_done', 'dpe_ab', 'dpe_fg']
SOURCE = "SDES, répertoire des logements locatifs des bailleurs sociaux (RPLS) au 1er janvier 2025"


def _r(v, digits=2):
    return round(v, digits) if v is not None else None


class SocialHousingService(TerritoryStatsService):
    MODEL = SocialHousingByTerritory
    DATA_KEY = "social_housing_data"
    LABEL = "logement social"
    EXTRA = {"source": SOURCE}
    EVOLUTION_METRICS = ["social_dwellings", "vacancy_rate", "mobility_rate", "avg_rent_m2"]

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in FIELDS}
        d = {k: _r(v) for k, v in c.items()}
        ls = c["social_dwellings"]
        rooms = total(c["rooms_1"], c["rooms_2"], c["rooms_3"], c["rooms_4"], c["rooms_5p"])
        fin = total(c["fin_plai"], c["fin_plus_after_77"], c["fin_plus_before_77"], c["fin_pls"], c["fin_pli"])
        d["qpv_share"] = pct(c["in_qpv"], ls)
        d["individual_share"] = pct(c["individual"], total(c["individual"], c["collective"]))
        d["small_share"] = pct(total(c["rooms_1"], c["rooms_2"]), rooms)          # T1-T2
        d["large_share"] = pct(c["rooms_5p"], rooms)                               # T5 ou plus
        d["plai_share"] = pct(c["fin_plai"], fin)                                  # très social
        d["intermediate_share"] = pct(total(c["fin_pls"], c["fin_pli"]), fin)      # PLS, PLI
        d["recent_share"] = pct(c["age_lt10"], ls)                                 # moins de 10 ans
        d["old_share"] = pct(c["age_ge60"], ls)                                    # 60 ans ou plus
        d["dpe_fg_share"] = pct(c["dpe_fg"], c["dpe_done"])                        # étiquette énergie F ou G
        d["dpe_ab_share"] = pct(c["dpe_ab"], c["dpe_done"])
        return d

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        data = result[self.DATA_KEY]
        years = sorted(data)
        base = data[years[0]].get("social_dwellings")
        for y in years:
            v = data[y].get("social_dwellings")
            data[y]["social_dwellings_index"] = round(v / base * 100, 1) if v is not None and base else None
        result["base_year"] = years[0]
        return result
