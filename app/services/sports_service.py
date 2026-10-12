"""
Pratique sportive — licences sportives (INJEP — MEOS, recensement des licences et clubs sportifs 2023 ; diffusion
Observatoire des territoires), table sports_by_territory (scripts/import_sports_by_territory.py). Licences rattachées
à la commune de résidence du licencié. France métropolitaine : moyenne des régions pondérée par la population.
"""
from app.models import SportsByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "licence_rate": "Licenciés sportifs pour 100 habitants",
    "licence_rate_15_29": "Licenciés de 15-29 ans pour 100 habitants de 15-29 ans",
    "licence_rate_30_59": "Licenciés de 30-59 ans pour 100 habitants de 30-59 ans",
    "girls_share_0_14": "Part des filles parmi les licenciés de 0-14 ans (%)",
    "women_share_15_29": "Part des femmes parmi les licenciés de 15-29 ans (%)",
    "women_share_30_59": "Part des femmes parmi les licenciés de 30-59 ans (%)",
    "women_share_60p": "Part des femmes parmi les licenciés de 60 ans ou plus (%)",
}


class SportsService(TerritoryStatsService):
    MODEL = SportsByTerritory
    DATA_KEY = "sports_data"
    LABEL = "licences sportives"
    EXTRA = {"indicators": INDICATORS,
             "source": "INJEP — MEOS, recensement des licences et clubs sportifs 2023 (Observatoire des territoires)"}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
