"""
Fragilités sanitaires et sociales — Observatoire interrégimes des situations de fragilité (Géofragilité :
Assurance maladie, Assurance retraite, MSA), millésime 2025, et APL de l'ANCT (2024), table fragilities_by_territory
(scripts/import_fragilities_by_territory.py).

Pourcentages publiés tels quels (pas d'effectifs) ; valeur absente = secret statistique (petits effectifs).
Ligne France (FM) : valeurs nationales publiées (france.csv) — France entière pour l'Observatoire, métropole pour l'APL.
"""
from app.models import FragilitiesByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

INDICATORS = {
    "no_gp_rate": "Bénéficiaires de 16 ans ou plus sans médecin traitant déclaré (%, interrégime)",
    "ald_rate": "Bénéficiaires de 16 ans ou plus en affection de longue durée (%, interrégime)",
    "invalidity_rate": "Bénéficiaires de 16 ans ou plus d'une pension d'invalidité (%, interrégime)",
    "c2s_rate": "Bénéficiaires de la complémentaire santé solidaire (%, régime général)",
    "no_dentist_rate": "Bénéficiaires de 16 ans ou plus sans consultation dentaire en 24 mois (%, régime général)",
    "no_colorectal_screening_rate": "50-74 ans éligibles sans dépistage du cancer colorectal (%)",
    "no_cervical_screening_rate": "Femmes de 25 à 65 ans sans dépistage du cancer du col de l'utérus (%)",
    "no_mammography_rate": "Femmes de 50 à 74 ans sans mammographie en 24 mois (%, régime général)",
    "no_gynecologist_rate": "Femmes de 20 à 64 ans sans consultation de gynécologue en 24 mois (%, régime général)",
    "no_flu_vaccine_65p_rate": "65 ans ou plus sans vaccination antigrippale en 24 mois (%, régime général)",
    "no_flu_vaccine_75p_rate": "75 ans ou plus éligibles sans vaccination antigrippale en 24 mois (%)",
    "apl_dentists": "Accessibilité potentielle localisée aux chirurgiens-dentistes (ETP pour 100 000 habitants, 2024)",
    "apl_gp_under65": "Accessibilité potentielle localisée aux médecins généralistes de moins de 65 ans (consultations par habitant, 2024)",
}
SOURCE = ("Observatoire interrégimes des situations de fragilité (Assurance maladie, Assurance retraite, MSA), 2025 ; "
          "ANCT, accessibilité potentielle localisée 2024")


class FragilitiesService(TerritoryStatsService):
    MODEL = FragilitiesByTerritory
    DATA_KEY = "fragilities_data"
    LABEL = "fragilités sanitaires et sociales"
    EXTRA = {"indicators": INDICATORS, "source": SOURCE, "apl_year": 2024}

    def year_data(self, row):
        return {k: num(getattr(row, k)) for k in INDICATORS}
