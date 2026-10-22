"""
pass Sport 2024 (ministère des Sports, activations journalières, campagne juin 2024 - février 2025) — table
pass_sport_by_territory (scripts/import_pass_sport_by_territory.py). Commune de résidence du bénéficiaire.
Taux de recours : pass activés par des 6-17 ans pour 100 habitants de 6-17 ans (recensement). France (FM) = métropole.
"""
from app.models import PassSportByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "activations": "Pass Sport activés (tous âges)",
    "activations_6_17": "Pass Sport activés par des 6-17 ans",
    "girls_6_17": "Pass Sport activés par des filles de 6-17 ans",
    "students": "Pass Sport activés par des étudiants boursiers",
    "pop_6_17": "Population de 6 à 17 ans (recensement)",
    "rate_6_17": "Pass Sport activés pour 100 jeunes de 6-17 ans",
    "girls_share_6_17": "Part des filles parmi les 6-17 ans bénéficiaires (%)",
}
SOURCE = "Ministère des Sports, pass Sport 2024 — activations (data.gouv.fr) ; INSEE, recensement de la population"


class PassSportService(TerritoryStatsService):
    MODEL = PassSportByTerritory
    DATA_KEY = "pass_sport_data"
    LABEL = "pass Sport"
    EXTRA = {"indicators": INDICATORS, "source": SOURCE, "campaign": "4 juin 2024 - 3 février 2025"}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
