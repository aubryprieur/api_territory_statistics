"""
Précarité énergétique logement (Géodip, Observatoire national de la précarité énergétique, 2022) — table
energy_poverty_by_territory (scripts/import_energy_poverty_by_territory.py).
Un ménage est en précarité énergétique logement quand ses dépenses théoriques d'énergie pour le logement dépassent 8 %
de ses ressources et que son niveau de vie est sous le 3e décile (30 % des ménages les plus modestes) ; estimation du
CGDD (modèle Prometheus). France (FM) = France métropolitaine : pas d'estimation pour l'outre-mer.
"""
from app.models import EnergyPovertyByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "energy_poverty_rate": "Part des ménages en précarité énergétique logement (%)",
    "energy_poverty_households": "Ménages en précarité énergétique logement",
}
SOURCE = "Géodip (ONPE, RARE), 2026 ; Insee, RP 2022 — estimation CGDD (modèle Prometheus), via l'Observatoire des territoires (ANCT)"
DEFINITION = ("Ménages dont les dépenses théoriques d'énergie pour le logement dépassent 8 % des ressources et dont le "
              "niveau de vie est parmi les 30 % les plus modestes (indicateur TEE_3D de l'ONPE).")


class EnergyPovertyService(TerritoryStatsService):
    MODEL = EnergyPovertyByTerritory
    DATA_KEY = "energy_poverty_data"
    LABEL = "précarité énergétique"
    EXTRA = {"indicators": INDICATORS, "source": SOURCE, "definition": DEFINITION}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
