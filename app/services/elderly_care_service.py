"""
Offre pour personnes âgées — INSEE, Base permanente des équipements 2025 (table elderly_care_by_territory,
scripts/import_elderly_care_by_territory.py) : établissements d'hébergement (Ehpad, résidences autonomie…) et places,
services de soins et d'aide à domicile implantés, places pour 1 000 personnes de 75 ans ou plus (recensement 2023).
France (FM) = France métropolitaine.
"""
from app.models import ElderlyCareByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "housing_facilities": "Établissements d'hébergement pour personnes âgées (Ehpad, résidences autonomie…)",
    "housing_places": "Places d'hébergement pour personnes âgées",
    "housing_no_capacity": "Établissements d'hébergement sans capacité renseignée",
    "home_nursing_services": "Services de soins infirmiers à domicile implantés",
    "home_help_services": "Services d'aide à domicile pour personnes âgées implantés",
    "pop_75p": "Population de 75 ans ou plus (2023)",
    "places_per_1000_75p": "Places d'hébergement pour 1 000 personnes de 75 ans ou plus",
}
SOURCE = "INSEE, Base permanente des équipements 2025 ; recensement de la population 2023"


class ElderlyCareService(TerritoryStatsService):
    MODEL = ElderlyCareByTerritory
    DATA_KEY = "elderly_care_data"
    LABEL = "offre pour personnes âgées"
    EXTRA = {"indicators": INDICATORS, "source": SOURCE, "population_year": 2023}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
