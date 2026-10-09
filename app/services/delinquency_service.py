"""
Délinquance et tranquillité publique — crimes et délits enregistrés par la police et la gendarmerie (SSMSI,
ministère de l'Intérieur, 2016-2025), table delinquency_by_territory.

Pour chaque indicateur : nombre, taux pour 1 000 habitants (pour 1 000 logements pour les cambriolages) et
`diffused` (False : petit effectif communal non diffusé par le SSMSI, taux et nombre à None). Faits comptés au lieu
de commission. Évolution par défaut 2020 → 2025.
"""
from app.models import DelinquencyByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "intrafamily_violence": {"label": "Violences physiques intrafamiliales", "unit": "victimes", "theme": "Atteintes aux personnes"},
    "other_physical_violence": {"label": "Violences physiques hors cadre familial", "unit": "victimes", "theme": "Atteintes aux personnes"},
    "sexual_violence": {"label": "Violences sexuelles", "unit": "victimes", "theme": "Atteintes aux personnes"},
    "homicide": {"label": "Homicides", "unit": "victimes", "theme": "Atteintes aux personnes"},
    "attempted_homicide": {"label": "Tentatives d'homicide", "unit": "victimes", "theme": "Atteintes aux personnes"},
    "armed_robbery": {"label": "Vols avec armes", "unit": "infractions", "theme": "Vols et cambriolages"},
    "violent_theft": {"label": "Vols violents sans arme", "unit": "infractions", "theme": "Vols et cambriolages"},
    "theft_without_violence": {"label": "Vols sans violence contre des personnes", "unit": "victimes entendues", "theme": "Vols et cambriolages"},
    "burglary": {"label": "Cambriolages de logement", "unit": "infractions", "theme": "Vols et cambriolages", "per": "logements"},
    "vehicle_theft": {"label": "Vols de véhicule", "unit": "véhicules", "theme": "Vols et cambriolages"},
    "theft_from_vehicle": {"label": "Vols dans les véhicules", "unit": "véhicules", "theme": "Vols et cambriolages"},
    "vehicle_accessory_theft": {"label": "Vols d'accessoires sur véhicules", "unit": "véhicules", "theme": "Vols et cambriolages"},
    "vandalism": {"label": "Destructions et dégradations volontaires", "unit": "infractions", "theme": "Tranquillité publique"},
    "drug_use": {"label": "Usage de stupéfiants", "unit": "mis en cause", "theme": "Tranquillité publique"},
    "drug_use_afd": {"label": "dont amendes forfaitaires délictuelles", "unit": "mis en cause", "theme": "Tranquillité publique"},
    "drug_use_non_afd": {"label": "Usage de stupéfiants hors amendes forfaitaires", "unit": "mis en cause", "theme": "Tranquillité publique"},
    "drug_trafficking": {"label": "Trafic de stupéfiants", "unit": "mis en cause", "theme": "Tranquillité publique"},
    "fraud": {"label": "Escroqueries et fraudes aux moyens de paiement", "unit": "victimes", "theme": "Escroqueries"},
}


class DelinquencyService(TerritoryStatsService):
    MODEL = DelinquencyByTerritory
    DATA_KEY = "delinquency_data"
    LABEL = "délinquance"
    EXTRA = {"indicators": INDICATORS,
             "source": "SSMSI, ministère de l'Intérieur — crimes et délits enregistrés par la police et la gendarmerie"}
    EVOLUTION_METRICS = [f"{k}_rate" for k in INDICATORS]

    def year_data(self, row):
        d = {"population": num(row.population), "dwellings": num(row.dwellings)}
        for k in INDICATORS:
            diffused = getattr(row, f"{k}_diffused")
            d[f"{k}_diffused"] = diffused
            d[f"{k}_count"] = num(getattr(row, f"{k}_count")) if diffused else None
            rate = num(getattr(row, f"{k}_rate")) if diffused else None
            d[f"{k}_rate"] = round(rate, 2) if rate is not None else None
        return d
