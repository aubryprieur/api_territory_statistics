"""
Catalogue de la synthèse des fragilités (onglet Synthèse du dashboard commune) : 9 enjeux, 40 indicateurs, tous des
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


def _i(key, label, theme, direction, source, field=None, unit="%", count=None, tab=None, need=False, sides=None):
    """need=True : indicateur de besoin (75 ans ou plus, familles nombreuses, HLM, jeunes chez leurs parents) —
    compté en alerte quand il est élevé, mais jamais présenté comme un point fort quand il est faible."""
    return {"key": key, "label": label, "theme": theme, "direction": direction, "source": source,
            "field": field or key, "unit": unit, "count": count, "tab": tab, "need": need, "sides": sides}


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
       count="pop_75p", tab="seniors", need=True),
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
    _i("energy_poverty_rate", "Ménages en précarité énergétique logement", "housing", "up", "energy_poverty",
       count="energy_poverty_households", tab="housing"),
    # Tranquillité publique
    _i("intrafamily_violence_rate", "Victimes de violences physiques intrafamiliales pour 1 000 habitants", "safety",
       "up", "delinquency", unit="‰", count="intrafamily_violence_count", tab="delinquency"),
]

INDICATOR_KEYS = [i["key"] for i in INDICATORS]

# Indicateurs de contexte : rangs calculés et affichés en tête des onglets (_fragility_ranks) et dans les « Repères » de
# l'onglet Synthèse, mais hors décompte des enjeux de fragilité (ni alerte ni niveau d'enjeu principal).
# Lecture « intensité de l'enjeu » (dashboard, bleu → rouge) :
#   "up"         : valeur élevée = enjeu plus marqué ; "down" : valeur faible = enjeu plus marqué
#   "neutral"    : indicateur de structure ; valeur élevée = public concerné plus nombreux, donc enjeu plus marqué
#                  (rang 100 = valeur la plus élevée), sans jugement positif ou négatif
#   "two_sided"  : les deux extrêmes sont des enjeux (forte baisse / forte hausse) ; intensité = écart à la médiane,
#                  sens indiqué par sides = (libellé valeur basse, libellé valeur haute)
CONTEXT_GROUPS = {
    "population": ("Population", "synthese"),
    "households": ("Ménages", "households"),
    "immigration": ("Immigrés et étrangers", "immigration"),
    "early_childhood": ("Petite enfance", "children_comparison"),
    "schooling": ("Scolarité", "schooling"),
    "economy": ("Tissu économique", "local_economy"),
    "rights": ("Accès aux droits", "caf_benefits"),
    "local_life": ("Vie locale", "local_life"),
}

GROWTH = ("forte baisse", "forte hausse")

CONTEXT_INDICATORS = [
    # Population : dynamique démographique
    _i("population_growth_rate", "Variation annuelle de la population entre les deux derniers recensements",
       "population", "two_sided", "history", field="annual_growth_rate", unit="%/an", tab="synthese", sides=GROWTH),
    _i("natural_growth_rate", "Part due au solde naturel (naissances - décès)", "population", "two_sided", "history",
       field="annual_natural_rate", unit="%/an", tab="synthese", sides=GROWTH),
    _i("migration_growth_rate", "Part due au solde migratoire apparent (arrivées - départs)", "population",
       "two_sided", "history", field="annual_migration_rate", unit="%/an", tab="synthese", sides=GROWTH),
    _i("dependency_ratio", "Rapport de dépendance (moins de 20 ans et 65 ans ou plus pour 100 personnes de 20-64 ans)",
       "population", "neutral", "population_structure", unit="pour 100", tab="synthese"),
    _i("newcomers_share", "Nouveaux arrivants (habitants venus d'une autre commune dans l'année)", "population",
       "neutral", "population_structure", field="newcomers_percentage", tab="synthese"),
    # Ménages
    _i("one_person_share", "Ménages d'une personne", "households", "neutral", "household",
       field="one_person_percentage", tab="households"),
    _i("alone_65p_share", "65 ans ou plus vivant seuls", "households", "up", "household",
       field="living_alone_rate_65_plus", tab="households"),
    _i("recent_movers_share", "Ménages emménagés depuis moins de 2 ans", "households", "neutral", "housing",
       field="recent_movers_percentage", tab="households"),
    # Familles
    _i("couples_with_children_share", "Couples avec enfants (part des ménages)", "families", "neutral", "family",
       field="couples_with_children_percentage", tab="families"),
    # Logement
    _i("social_housing_mobility_rate", "Taux de mobilité dans le parc social (emménagements dans l'année)",
       "housing", "down", "social_housing", field="mobility_rate", tab="housing"),
    # Immigrés et étrangers
    _i("immigrant_share", "Part des immigrés dans la population", "immigration", "neutral", "immigration",
       field="immigrant_rate", tab="immigration"),
    _i("foreigner_share", "Part des étrangers dans la population", "immigration", "neutral", "immigration",
       field="foreigner_rate", tab="immigration"),
    _i("immigrant_unemployment_rate", "Taux de chômage des immigrés", "immigration", "up", "immigration",
       field="imm_unemployment_rate", tab="immigration"),
    # Petite enfance (avec childcare_coverage_rate de l'enjeu Familles)
    _i("age_0_2_share", "Part des moins de 3 ans dans la population", "early_childhood", "neutral",
       "population_structure", field="age_0_2_percentage", tab="children_comparison"),
    _i("age_3_5_share", "Part des 3-5 ans dans la population", "early_childhood", "neutral", "population_structure",
       field="age_3_5_percentage", tab="children_comparison"),
    _i("births_change", "Évolution des naissances (moyenne des 3 dernières années / 3 premières)", "early_childhood",
       "two_sided", "births", tab="children_comparison", sides=GROWTH),
    _i("eaje_coverage_rate", "Places en accueil collectif (crèches) pour 100 enfants de moins de 3 ans",
       "early_childhood", "down", "childcare", field="rate_eaje", unit="pour 100", tab="children_comparison"),
    _i("childminder_coverage_rate", "Places chez les assistantes maternelles pour 100 enfants de moins de 3 ans",
       "early_childhood", "down", "childcare", field="rate_childminder", unit="pour 100", tab="children_comparison"),
    # Enfance, jeunesse
    _i("age_6_10_share", "Part des 6-10 ans dans la population", "youth", "neutral", "population_structure",
       field="age_6_10_percentage", tab="youth"),
    _i("age_11_14_share", "Part des 11-14 ans dans la population", "youth", "neutral", "population_structure",
       field="age_11_14_percentage", tab="youth"),
    _i("age_15_17_share", "Part des 15-17 ans dans la population", "youth", "neutral", "population_structure",
       field="age_15_17_percentage", tab="youth"),
    _i("age_18_24_share", "Part des 18-24 ans dans la population", "youth", "neutral", "population_structure",
       field="age_18_24_percentage", tab="youth"),
    _i("licence_rate_15_29", "Licenciés sportifs de 15-29 ans pour 100 habitants du même âge", "youth", "down",
       "sports", unit="pour 100", tab="youth"),
    # Scolarité (avec schooling_rate_15_17 de l'enjeu Jeunesse)
    _i("schooling_rate_2", "Taux de scolarisation à 2 ans", "schooling", "neutral", "education", tab="schooling"),
    _i("schooling_rate_3_5", "Taux de scolarisation des 3-5 ans", "schooling", "down", "education", tab="schooling"),
    _i("schooling_rate_18_24", "Taux de scolarisation des 18-24 ans", "schooling", "neutral", "education",
       tab="schooling"),
    _i("remoteness_college", "Indice d'éloignement des collèges de la commune", "schooling", "up", "schools_college",
       unit="indice", tab="schooling"),
    _i("ips_ecole", "Indice de position sociale (IPS) des écoles de la commune", "schooling", "down", "schools_ecole",
       unit="indice", tab="schooling"),
    _i("ips_college", "Indice de position sociale (IPS) des collèges de la commune", "schooling", "down", "schools_college",
       unit="indice", tab="schooling"),
    _i("ips_lycee", "Indice de position sociale (IPS) des lycées de la commune", "schooling", "down", "schools_lycee",
       unit="indice", tab="schooling"),
    # Emploi et activité
    _i("youth_employment_rate", "Taux d'emploi des 15-24 ans", "employment", "down", "employment",
       field="employment_rate_15_24", tab="employment"),
    _i("part_time_share", "Salariés à temps partiel", "employment", "up", "employment",
       field="salaried_part_time_percentage", tab="employment"),
    _i("upper_to_working_ratio", "Cadres et professions intermédiaires pour 100 employés et ouvriers", "employment",
       "down", "population_structure", field="upper_to_working_class_ratio", unit="pour 100", tab="employment"),
    # Tissu économique
    _i("employment_concentration", "Concentration d'emploi (emplois pour 100 actifs occupés résidents)", "economy",
       "two_sided", "employment", unit="pour 100", tab="local_economy",
       sides=("commune surtout résidentielle", "pôle d'emploi")),
    _i("presential_posts_share", "Postes salariés de l'économie présentielle", "economy", "neutral",
       "economic_fabric", tab="local_economy"),
    _i("business_creation_rate", "Créations d'entreprises par an pour 1 000 habitants", "economy", "down",
       "business_creations", unit="‰", tab="local_economy"),
    _i("individual_creations_share", "Part des entreprises individuelles parmi les créations", "economy", "neutral",
       "business_creations", tab="local_economy"),
    # Accès aux droits (avec RSA, prime d'activité, C2S, ARS)
    _i("caf_coverage_rate", "Population couverte par la CAF", "rights", "neutral", "caf", count="all_persons",
       tab="caf_benefits"),
    _i("housing_benefit_rate", "Population couverte par une aide au logement", "rights", "up", "caf",
       count="housing_persons", tab="caf_benefits"),
    # Seniors
    _i("aging_index", "Indice de vieillissement (65 ans ou plus pour 100 moins de 20 ans)", "seniors", "neutral",
       "population_structure", unit="indice", tab="seniors"),
    _i("elderly_generations_index", "Indice d'évolution des générations âgées (60-74 ans pour 100 de 75 ans ou plus)",
       "seniors", "neutral", "population_structure", unit="indice", tab="seniors"),
    # Vie locale (avec licence_rate_0_14 de l'enjeu Jeunesse)
    _i("licence_rate", "Licenciés sportifs pour 100 habitants", "local_life", "down", "sports", unit="pour 100",
       tab="local_life"),
    _i("licence_rate_60p", "Licenciés sportifs de 60 ans ou plus pour 100 habitants du même âge", "local_life",
       "down", "sports", unit="pour 100", tab="local_life"),
    _i("associations_rate", "Associations en activité pour 1 000 habitants", "local_life", "down", "associations",
       unit="‰", count="associations_active", tab="local_life"),
    _i("presidential_turnout", "Participation au 1er tour de l'élection présidentielle", "local_life", "down", "sdg",
       tab="local_life"),
    _i("municipal_turnout", "Participation au 1er tour des élections municipales", "local_life", "down",
       "municipal_elections", field="turnout_rate", count="voters", tab="local_life"),
    # Délinquance (faits constatés : reflètent aussi l'activité des services et le recours à la plainte)
    _i("sexual_violence_rate", "Victimes de violences sexuelles pour 1 000 habitants", "safety", "up", "delinquency",
       unit="‰", count="sexual_violence_count", tab="delinquency"),
    _i("drug_use_rate", "Mis en cause pour usage de stupéfiants pour 1 000 habitants", "safety", "up", "delinquency",
       unit="‰", count="drug_use_count", tab="delinquency"),
]
for _c in CONTEXT_INDICATORS:
    _c["context"] = True
for _c in INDICATORS:
    _c["context"] = False

ALL_INDICATORS = INDICATORS + CONTEXT_INDICATORS
BY_KEY = {i["key"]: i for i in ALL_INDICATORS}

# Indicateurs affichés dans l'encart « Position parmi les communes » de chaque onglet du dashboard (et dans le repère
# de l'onglet dans la Synthèse), dans l'ordre. Un indicateur de fragilité peut être présenté dans un onglet autre que
# celui de son enjeu : il continue de compter dans son enjeu (ex. chômage des 15-24 ans : onglet Emploi, enjeu Jeunesse).
TAB_KEYS = {
    "synthese": ["population_growth_rate", "natural_growth_rate", "migration_growth_rate", "dependency_ratio",
                 "newcomers_share"],
    "households": ["one_person_share", "alone_65p_share", "alone_80p_share", "recent_movers_share"],
    "families": ["single_parent_share", "large_families_share", "couples_with_children_share", "ars_families_rate"],
    "housing": ["overcrowding_rate", "vacancy_rate", "no_car_share", "social_tenants_share", "energy_poverty_rate",
                "social_housing_mobility_rate"],
    "children_comparison": ["age_0_2_share", "age_3_5_share", "births_change", "childcare_coverage_rate",
                            "eaje_coverage_rate", "childminder_coverage_rate", "schooling_rate_2"],
    "youth": ["age_6_10_share", "age_11_14_share", "age_15_17_share", "age_18_24_share", "licence_rate_15_29",
              "young_with_parents_share"],
    "schooling": ["schooling_rate_2", "schooling_rate_3_5", "schooling_rate_15_17", "schooling_rate_18_24",
                  "remoteness_college", "ips_ecole", "ips_college", "ips_lycee"],
    "diplomas": ["no_diploma_share", "higher_education_share", "young_no_diploma_rate", "young_neet_rate"],
    "employment": ["unemployment_rate", "employment_rate", "women_employment_rate", "job_seekers_rate",
                   "youth_employment_rate", "youth_unemployment_rate", "fixed_term_share", "part_time_share",
                   "upper_to_working_ratio"],
    "local_economy": ["employment_concentration", "presential_posts_share", "business_creation_rate",
                      "individual_creations_share"],
    "revenues_poverty": ["poverty_rate", "median_living_standard", "social_benefits_share", "taxed_households_share",
                         "c2s_rate"],
    "immigration": ["immigrant_share", "foreigner_share", "immigrant_unemployment_rate"],
    "caf_benefits": ["caf_coverage_rate", "rsa_population_rate", "ppa_population_rate", "housing_benefit_rate",
                     "ars_families_rate", "c2s_rate"],
    "health": ["gp_accessibility", "no_gp_rate", "ald_rate", "no_dentist_rate", "no_colorectal_screening_rate"],
    "seniors": ["seniors_at_risk_share", "min_old_age_rate", "alone_80p_share", "age_75p_share", "elderly_places_rate",
                "aging_index", "elderly_generations_index"],
    "local_life": ["licence_rate", "licence_rate_0_14", "licence_rate_60p", "associations_rate", "presidential_turnout",
                   "municipal_turnout"],
    "delinquency": ["intrafamily_violence_rate", "sexual_violence_rate", "drug_use_rate"],
}

# Niveau d'un enjeu de contexte (tuile de la Synthèse) : indicateurs jugés (up / down) de l'onglet correspondant
CONTEXT_GROUP_KEYS = {g: TAB_KEYS[tab] for g, (_, tab) in CONTEXT_GROUPS.items()}
