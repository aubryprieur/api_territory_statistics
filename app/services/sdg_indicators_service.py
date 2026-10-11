"""
Indicateurs territoriaux de développement durable (INSEE / SDES, base « ODD ») sélectionnés pour l'analyse des
besoins sociaux, table sdg_indicators_by_territory. Les indicateurs n'ont pas tous les mêmes millésimes : chaque
valeur est renvoyée pour les années où elle existe (`available_years_by_indicator`).
"""
from app.models import SdgIndicatorsByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "young_neet_rate": "Jeunes de 18-24 ans non insérés (ni en emploi, ni en études), parmi les non-scolarisés (%)",
    "young_no_diploma_rate": "Jeunes de 20-24 ans sortis du système scolaire sans diplôme (%)",
    "long_term_unemployed_share": "Part des chômeurs depuis plus d'un an (%)",
    "employment_gap_women_men": "Écart de taux d'emploi femmes - hommes, 15-64 ans (points)",
    "employment_gap_women_men_25_54": "Écart de taux d'emploi femmes - hommes, 25-54 ans (points)",
    "ess_jobs_share": "Part des emplois de l'économie sociale et solidaire (%)",
    "gp_accessibility": "Accessibilité potentielle localisée aux médecins généralistes (consultations par an et par habitant)",
    "commute_minutes": "Durée médiane du trajet domicile-travail (minutes)",
    "commute_km": "Distance médiane du trajet domicile-travail (km)",
    "commute_car_share": "Déplacements domicile-travail en voiture (%)",
    "commute_public_transport_share": "Déplacements domicile-travail en transports en commun (%)",
    "commute_walk_share": "Déplacements domicile-travail à pied (%)",
    "commute_bike_share": "Déplacements domicile-travail à vélo (%)",
    "commute_two_wheels_share": "Déplacements domicile-travail en deux-roues (%)",
    "commute_no_transport_share": "Pas de déplacement domicile-travail (%)",
    "social_housing_share": "Logements sociaux parmi les résidences principales (%)",
    "vacant_housing_share": "Logements vacants (%)",
    "presidential_turnout": "Participation au 1er tour de l'élection présidentielle (%)",
}


class SdgIndicatorsService(TerritoryStatsService):
    MODEL = SdgIndicatorsByTerritory
    DATA_KEY = "sdg_data"
    LABEL = "indicateurs de développement durable"
    EXTRA = {"indicators": INDICATORS,
             "source": "INSEE / SDES — indicateurs territoriaux de développement durable (ODD)"}
    EVOLUTION_METRICS = []

    def year_data(self, row):
        return {k: (round(num(getattr(row, k)), 2) if num(getattr(row, k)) is not None else None) for k in INDICATORS}

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        data = result[self.DATA_KEY]
        result["available_years_by_indicator"] = {
            k: sorted(y for y, d in data.items() if d.get(k) is not None) for k in INDICATORS}
        # On ne renvoie que les années où au moins un indicateur est renseigné
        result[self.DATA_KEY] = {y: d for y, d in data.items() if any(v is not None for v in d.values())}
        result["available_years"] = sorted(result[self.DATA_KEY])
        return result
