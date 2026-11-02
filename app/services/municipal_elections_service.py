"""
Élections municipales, 1er tour (ministère de l'Intérieur, résultats par commune) — table
municipal_elections_by_territory (scripts/import_municipal_elections_by_territory.py).
Taux de participation = votants / inscrits. EPCI, départements, régions et France métropolitaine (FM) : sommes des
communes.
"""
from app.models import MunicipalElectionsByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "registered": "Inscrits",
    "voters": "Votants",
    "expressed": "Suffrages exprimés",
    "blank": "Votes blancs",
    "null": "Votes nuls",
    "turnout_rate": "Participation au 1er tour (% des inscrits)",
    "blank_null_rate": "Blancs et nuls (% des votants)",
}
SOURCE = "Ministère de l'Intérieur, élections municipales — résultats du 1er tour par commune (data.gouv.fr)"


class MunicipalElectionsService(TerritoryStatsService):
    MODEL = MunicipalElectionsByTerritory
    DATA_KEY = "municipal_elections_data"
    LABEL = "élections municipales"
    EXTRA = {"indicators": INDICATORS, "source": SOURCE, "round": 1}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
