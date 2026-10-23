"""
Catalogue de la synthèse des fragilités (onglet Synthèse du dashboard commune) : 9 enjeux, 39 indicateurs, tous des
taux ou des valeurs relatives (jamais des effectifs : un effectif dépend de la taille de la commune).

Chaque indicateur : key, label, theme, direction ("up" = plus élevé = plus fragile ; "down" = l'inverse), unit
(affichage : "%", "€", "‰", "pour 100", "indice"), source (lecture dans scripts/import_fragility_synthesis.py),
field (clé dans la source), count (effectif de la commune à afficher, optionnel), tab (onglet du dashboard).
Partagé par l'import (calcul des rangs) et le service (niveau de chaque enjeu).
"""

THEMES = {
    "poverty": "Pauvreté et ressources",
    "employment": "Emploi et insertion",
    "youth": "Jeunesse",
    "diplomas": "Diplômes et formation",
    "families": "Familles",
    "seniors": "Seniors",
    "health": "Santé et accès aux soins",
    "housing": "Logement et mobilité",
    "safety": "Tranquillité publique",
}

ALERT_THRESHOLD = 80     # rang ≥ 80 : parmi les 20 % de communes les plus touchées
STRENGTH_THRESHOLD = 20  # rang ≤ 20 : parmi les 20 % de communes les moins touchées


def _i(key, label, theme, direction, source, field=None, unit="%", count=None, tab=None, need=False):
    """need=True : indicateur de besoin (75 ans ou plus, familles nombreuses, HLM, jeunes chez leurs parents) —
    compté en alerte quand il est élevé, mais jamais présenté comme un point fort quand il est faible."""
    return {"key": key, "label": label, "theme": theme, "direction": direction, "source": source,
            "field": field or key, "unit": unit, "count": count, "tab": tab, "need": need}


INDICATORS = [
    # Pauvreté et ressources
    _i("poverty_rate", "Taux de pauvreté", "poverty", "up", "revenues", tab="revenues_poverty"),
    _i("median_living_standard", "Revenu disponible médian par unité de consommation", "poverty", "down", "revenues",
       unit="€", tab="revenues_poverty"),
    _i("social_benefits_share", "Part des prestations sociales dans le revenu disponible", "poverty", "up", "revenues",
       field="share_social_benefits", tab="revenues_poverty"),
    _i("taxed_households_share", "Foyers fiscaux imposés", "poverty", "down", "tax_households", field="taxed_share",
       tab="revenues_poverty"),
    _i("rsa_population_rate", "Population couverte par le RSA", "poverty", "up", "caf", count="rsa_persons",
       tab="caf_benefits"),
    _i("ppa_population_rate", "Population couverte par la prime d'activité", "poverty", "up", "caf",
       count="ppa_persons", tab="caf_benefits"),
    _i("c2s_rate", "Bénéficiaires de la complémentaire santé solidaire (régime général)", "poverty", "up",
       "fragilities", tab="caf_benefits"),
    # Emploi et insertion
    _i("unemployment_rate", "Taux de chômage des 15-64 ans", "employment", "up", "employment",
       field="unemployment_rate_15_64", count="unemployed_15_64", tab="employment"),
    _i("employment_rate", "Taux d'emploi des 15-64 ans", "employment", "down", "employment",
       field="employment_rate_15_64", tab="employment"),
    _i("women_employment_rate", "Taux d'emploi des femmes de 15-64 ans", "employment", "down", "employment",
       field="employment_rate_15_64_women", tab="employment"),
    _i("job_seekers_rate", "Demandeurs d'emploi (catégories A, B, C) pour 100 actifs", "employment", "up",
       "job_seekers", unit="pour 100", count="abc", tab="employment"),
    _i("fixed_term_share", "Salariés en contrat précaire (CDD, intérim, aidés, apprentis)", "employment", "up",
       "employment", field="fixed_term_percentage", tab="employment"),
    # Jeunesse et éducation
    _i("schooling_rate_15_17", "Taux de scolarisation des 15-17 ans", "youth", "down", "education", tab="schooling"),
    _i("young_no_diploma_rate", "20-24 ans sortis du système scolaire sans diplôme", "diplomas", "up", "sdg",
       tab="diplomas"),
    _i("young_neet_rate", "18-24 ans ni en emploi ni en études", "diplomas", "up", "sdg", tab="diplomas"),
    _i("youth_unemployment_rate", "Taux de chômage des 15-24 ans", "youth", "up", "employment",
       field="unemployment_rate_15_24", count="unemployed_15_24", tab="employment"),
    _i("no_diploma_share", "15 ans ou plus non scolarisés sans diplôme", "diplomas", "up", "education",
       field="no_diploma_percentage", tab="diplomas"),
    _i("licence_rate_0_14", "Licenciés sportifs de moins de 15 ans (pour 100)", "youth", "down", "sports",
       unit="pour 100", tab="local_life"),
    _i("young_with_parents_share", "20-24 ans vivant ni seuls ni en couple (principalement chez leurs parents)",
       "youth", "up", "cfm", count="young_with_parents", tab="youth", need=True),
    _i("higher_education_share", "15 ans ou plus non scolarisés diplômés du supérieur", "diplomas", "down",
       "education", field="higher_education_percentage", tab="diplomas"),
    # Familles
    _i("single_parent_share", "Familles monoparentales", "families", "up", "family",
       field="single_parent_families_percentage", count="single_parent_families", tab="families"),
    _i("large_families_share", "Familles nombreuses (3 enfants ou plus)", "families", "up", "family",
       field="large_families_percentage", count="total_large_families", tab="families", need=True),
    _i("ars_families_rate", "Familles percevant l'allocation de rentrée scolaire (pour 100 familles avec enfants)",
       "families", "up", "caf", unit="pour 100", count="ars_households", tab="caf_benefits"),
    _i("childcare_coverage_rate", "Places d'accueil du jeune enfant pour 100 enfants de moins de 3 ans", "families",
       "down", "childcare", field="rate_global", unit="pour 100", tab="children_comparison"),
    # Seniors
    _i("seniors_at_risk_share", "Retraités à risque de fragilité sociale", "seniors", "up", "senior_fragilities",
       field="at_risk_share", count="at_risk_count", tab="seniors"),
    _i("min_old_age_rate", "Retraités au minimum vieillesse", "seniors", "up", "senior_fragilities", tab="seniors"),
    _i("alone_80p_share", "80 ans ou plus vivant seuls", "seniors", "up", "household",
       field="living_alone_rate_80_plus", count="living_alone_80_plus", tab="households"),
    _i("age_75p_share", "Part des 75 ans ou plus dans la population", "seniors", "up", "population",
       count="pop_75p", tab="synthese", need=True),
    _i("elderly_places_rate", "Places d'hébergement pour 1 000 personnes de 75 ans ou plus", "seniors", "down",
       "elderly_care", field="places_per_1000_75p", unit="‰", tab="seniors"),
    # Santé et accès aux soins
    _i("gp_accessibility", "Accessibilité aux médecins généralistes (consultations par habitant)", "health", "down",
       "sdg", unit="indice", tab="health"),
    _i("no_gp_rate", "Sans médecin traitant déclaré (16 ans ou plus)", "health", "up", "fragilities", tab="health"),
    _i("ald_rate", "En affection de longue durée (16 ans ou plus)", "health", "up", "fragilities", tab="health"),
    _i("no_dentist_rate", "Sans consultation dentaire depuis 24 mois", "health", "up", "fragilities", tab="health"),
    _i("no_colorectal_screening_rate", "50-74 ans sans dépistage du cancer colorectal", "health", "up", "fragilities",
       tab="health"),
    # Logement et mobilité
    _i("overcrowding_rate", "Résidences principales suroccupées", "housing", "up", "housing", tab="housing"),
    _i("vacancy_rate", "Logements vacants", "housing", "up", "housing", tab="housing"),
    _i("no_car_share", "Ménages sans voiture", "housing", "up", "housing", field="no_car_percentage", tab="housing"),
    _i("social_tenants_share", "Ménages locataires d'un logement HLM", "housing", "up", "housing",
       field="tenants_social_percentage", tab="housing", need=True),
    # Tranquillité publique
    _i("intrafamily_violence_rate", "Victimes de violences physiques intrafamiliales pour 1 000 habitants", "safety",
       "up", "delinquency", unit="‰", count="intrafamily_violence_count", tab="delinquency"),
]

INDICATOR_KEYS = [i["key"] for i in INDICATORS]

# Indicateurs de contexte : rangs calculés et affichés en tête des onglets thématiques (_fragility_ranks) et dans les
# « Repères » de l'onglet Synthèse, mais hors synthèse (ni enjeu, ni alerte, ni point fort).
# direction "neutral" : indicateur de structure, classé du plus faible (0) au plus élevé (100), sans jugement.
CONTEXT_GROUPS = {
    "population": ("Population", "synthese"),
    "households": ("Ménages", "households"),
    "immigration": ("Immigrés et étrangers", "immigration"),
    "early_childhood": ("Petite enfance", "children_comparison"),
    "schooling": ("Scolarité", "schooling"),
    "rights": ("Accès aux droits", "caf_benefits"),
    "local_life": ("Vie locale", "local_life"),
}

CONTEXT_INDICATORS = [
    # Population
    _i("age_lt20_share", "Part des moins de 20 ans", "population", "neutral", "population_structure",
       field="age_lt20_percentage", tab="synthese"),
    _i("age_ge65_share", "Part des 65 ans ou plus", "population", "neutral", "population_structure",
       field="age_ge65_percentage", tab="synthese"),
    _i("youth_index", "Indice de jeunesse (moins de 20 ans pour 100 personnes de 60 ans ou plus)", "population",
       "neutral", "population_structure", unit="indice", tab="synthese"),
    # Ménages
    _i("one_person_share", "Ménages d'une personne", "households", "neutral", "household",
       field="one_person_percentage", tab="households"),
    _i("alone_65p_share", "65 ans ou plus vivant seuls", "households", "up", "household",
       field="living_alone_rate_65_plus", tab="households"),
    # Immigrés et étrangers
    _i("immigrant_share", "Part des immigrés dans la population", "immigration", "neutral", "immigration",
       field="immigrant_rate", tab="immigration"),
    _i("foreigner_share", "Part des étrangers dans la population", "immigration", "neutral", "immigration",
       field="foreigner_rate", tab="immigration"),
    _i("immigrant_unemployment_rate", "Taux de chômage des immigrés", "immigration", "up", "immigration",
       field="imm_unemployment_rate", tab="immigration"),
    # Petite enfance (avec childcare_coverage_rate de l'enjeu Familles)
    _i("eaje_coverage_rate", "Places en accueil collectif (crèches) pour 100 enfants de moins de 3 ans",
       "early_childhood", "down", "childcare", field="rate_eaje", unit="pour 100", tab="children_comparison"),
    _i("childminder_coverage_rate", "Places chez les assistantes maternelles pour 100 enfants de moins de 3 ans",
       "early_childhood", "down", "childcare", field="rate_childminder", unit="pour 100", tab="children_comparison"),
    # Scolarité (avec schooling_rate_15_17 de l'enjeu Jeunesse)
    _i("schooling_rate_2", "Taux de scolarisation à 2 ans", "schooling", "neutral", "education", tab="schooling"),
    _i("schooling_rate_3_5", "Taux de scolarisation des 3-5 ans", "schooling", "down", "education", tab="schooling"),
    _i("schooling_rate_18_24", "Taux de scolarisation des 18-24 ans", "schooling", "neutral", "education",
       tab="schooling"),
    # Accès aux droits (avec RSA, prime d'activité, C2S, ARS)
    _i("caf_coverage_rate", "Population couverte par la CAF", "rights", "neutral", "caf", count="all_persons",
       tab="caf_benefits"),
    _i("housing_benefit_rate", "Population couverte par une aide au logement", "rights", "up", "caf",
       count="housing_persons", tab="caf_benefits"),
    # Vie locale (avec licence_rate_0_14 de l'enjeu Jeunesse)
    _i("licence_rate", "Licenciés sportifs pour 100 habitants", "local_life", "down", "sports", unit="pour 100",
       tab="local_life"),
    _i("licence_rate_60p", "Licenciés sportifs de 60 ans ou plus pour 100 habitants du même âge", "local_life",
       "down", "sports", unit="pour 100", tab="local_life"),
    _i("associations_rate", "Associations en activité pour 1 000 habitants", "local_life", "down", "associations",
       unit="‰", count="associations_active", tab="local_life"),
    _i("presidential_turnout", "Participation au 1er tour de l'élection présidentielle", "local_life", "down", "sdg",
       tab="local_life"),
]
for _c in CONTEXT_INDICATORS:
    _c["context"] = True
for _c in INDICATORS:
    _c["context"] = False

ALL_INDICATORS = INDICATORS + CONTEXT_INDICATORS
BY_KEY = {i["key"]: i for i in ALL_INDICATORS}

# Indicateurs repris dans chaque groupe de contexte (encadré de l'onglet et repère de la Synthèse), dans l'ordre
CONTEXT_GROUP_KEYS = {
    "population": ["age_lt20_share", "age_ge65_share", "age_75p_share", "youth_index"],
    "households": ["one_person_share", "alone_65p_share", "alone_80p_share", "single_parent_share"],
    "immigration": ["immigrant_share", "foreigner_share", "immigrant_unemployment_rate"],
    "early_childhood": ["childcare_coverage_rate", "eaje_coverage_rate", "childminder_coverage_rate",
                        "schooling_rate_2"],
    "schooling": ["schooling_rate_2", "schooling_rate_3_5", "schooling_rate_15_17", "schooling_rate_18_24"],
    "rights": ["caf_coverage_rate", "rsa_population_rate", "ppa_population_rate", "housing_benefit_rate",
               "ars_families_rate", "c2s_rate"],
    "local_life": ["licence_rate", "licence_rate_0_14", "licence_rate_60p", "associations_rate",
                   "presidential_turnout"],
}
