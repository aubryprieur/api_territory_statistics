"""
Fragilités des retraités et des seniors — Observatoire interrégimes des situations de fragilité (Géofragilité :
Assurance maladie, Assurance retraite, MSA), retraités et assurés de 55 ans ou plus, interrégime, millésime 2025
(score de non-recours aux soins : 2024). Table senior_fragilities_by_territory
(scripts/import_senior_fragilities_by_territory.py).

Parts et scores publiés tels quels ; valeur absente = secret statistique (petits effectifs). Part des retraités à
risque de fragilité sociale, nombre de retraités et évolution 2017-2025 : EPCI, département, région et France = sommes
des communes ayant une valeur. Ligne France (FM) = France entière, outre-mer compris (valeurs publiées sur le site).
"""
from app.models import SeniorFragilitiesByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "social_fragility_score": "Score moyen de fragilité sociale des retraités",
    "at_risk_share": "Retraités à risque de fragilité sociale (%)",
    "at_risk_count": "Retraités à risque de fragilité sociale (nombre)",
    "retirees_count": "Retraités de l'interrégime (nombre)",
    "retirees_change_rate": "Évolution du nombre de retraités 2017-2025 (%)",
    "min_old_age_rate": "Retraités au minimum vieillesse (%)",
    "csg_exempt_rate": "Retraités exonérés de CSG (%)",
    "csg_low_rate": "Retraités à la CSG au taux réduit (%)",
    "survivor_pension_rate": "Retraités bénéficiaires d'une pension de réversion (%)",
    "invalidity_inaptitude_rate": "Retraités ex-invalides ou partis au titre de l'inaptitude (%)",
    "incomplete_career_rate": "Retraités partis à l'âge du taux plein avec une carrière incomplète (%)",
    "css_free_rate": "55 ans ou plus bénéficiaires de la complémentaire santé solidaire sans participation (%)",
    "no_care_rate": "55 ans ou plus sans recours aux soins (%)",
    "no_gp_rate": "55 ans ou plus sans médecin traitant déclaré (%)",
    "ald_rate": "55 ans ou plus en affection de longue durée (%)",
    "care_nonuse_score": "Score moyen de fragilité liée au non-recours aux soins des seniors (2024)",
}
SOURCE = ("Observatoire interrégimes des situations de fragilité (Assurance maladie, Assurance retraite, MSA), "
          "retraités et assurés de 55 ans ou plus, interrégime, 2025")


class SeniorFragilitiesService(TerritoryStatsService):
    MODEL = SeniorFragilitiesByTerritory
    DATA_KEY = "senior_fragilities_data"
    LABEL = "fragilités des retraités et des seniors"
    EXTRA = {"indicators": INDICATORS, "source": SOURCE, "care_nonuse_year": 2024, "change_start_year": 2017}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
