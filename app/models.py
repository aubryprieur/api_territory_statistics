from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, func, Index, UniqueConstraint
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

class Birth(Base):
    __tablename__ = "births"

    id = Column(Integer, primary_key=True, index=True)
    geo = Column(String, nullable=False)
    geo_object = Column(String, nullable=False)
    time_period = Column(Integer, nullable=False)
    obs_value = Column(Float, nullable=False)

class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geo_code = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    total_households = Column(Float, nullable=True)
    single_men = Column(Float, nullable=True)
    single_women = Column(Float, nullable=True)
    couples_with_children = Column(Float, nullable=True)
    single_parent_families = Column(Float, nullable=True)
    single_fathers = Column(Float, nullable=True)
    single_mothers = Column(Float, nullable=True)
    couples_without_children = Column(Float, nullable=True)
    large_families = Column(Float, nullable=True)
    children_under_24_no_sibling = Column(Float, nullable=True)
    children_under_24_one_sibling = Column(Float, nullable=True)
    children_under_24_two_siblings = Column(Float, nullable=True)
    children_under_24_three_siblings = Column(Float, nullable=True)
    children_under_24_four_or_more_siblings = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GeoCode(Base):
    __tablename__ = "geo_codes"

    codgeo = Column(String(10), primary_key=True, index=True)  # Code commune
    libgeo = Column(String, nullable=False)  # Nom de la commune
    epci = Column(String(20), nullable=True)  # Code EPCI
    libepci = Column(String, nullable=True)  # Nom de l'EPCI
    dep = Column(String(5), nullable=False)  # Département
    reg = Column(String(5), nullable=False)  # Région

class Schooling(Base):
    __tablename__ = "schooling"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geo_code = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    age = Column(String(3), nullable=False)  # Adapté à 3 caractères
    sex = Column(String(1), nullable=False)
    education_status = Column(String(1), nullable=True)
    number = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class SchoolingSummary(Base):
    """Pré-agrégation de `schooling` par commune et année (voir migration a3c5d7e9f1b2)."""
    __tablename__ = "schooling_summary"

    geo_code = Column(Text, primary_key=True)
    year = Column(Integer, primary_key=True)
    total_2y = Column(Float, nullable=False, default=0)
    schooled_2y = Column(Float, nullable=False, default=0)
    total_3_5y = Column(Float, nullable=False, default=0)
    schooled_3_5y = Column(Float, nullable=False, default=0)

class FamilyByTerritory(Base):
    """Familles RP INSEE (DS_RP_FAMILLE_COMP) à toutes les échelles — voir migration b4d6f8a0c2e3."""
    __tablename__ = "families_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2012, 2017, 2023
    total_families = Column(Float)
    couples_with_children = Column(Float)
    couples_without_children = Column(Float)
    single_parent_families = Column(Float)
    single_fathers = Column(Float)
    single_mothers = Column(Float)
    blended_families = Column(Float)        # 2023 uniquement
    traditional_families = Column(Float)    # 2023 uniquement
    families_0_children = Column(Float)
    families_1_child = Column(Float)
    families_2_children = Column(Float)
    families_3_children = Column(Float)
    families_4_plus_children = Column(Float)
    # Enfants de moins de 2 ans / de 2 à 5 ans selon l'activité des parents (2023, TD famille)
    children_lt2_father_employed = Column(Float)
    children_lt2_father_not_employed = Column(Float)
    children_lt2_mother_employed = Column(Float)
    children_lt2_mother_not_employed = Column(Float)
    children_lt2_couple_both_employed = Column(Float)
    children_lt2_couple_man_only_employed = Column(Float)
    children_lt2_couple_woman_only_employed = Column(Float)
    children_lt2_couple_none_employed = Column(Float)
    children_2_5_father_employed = Column(Float)
    children_2_5_father_not_employed = Column(Float)
    children_2_5_mother_employed = Column(Float)
    children_2_5_mother_not_employed = Column(Float)
    children_2_5_couple_both_employed = Column(Float)
    children_2_5_couple_man_only_employed = Column(Float)
    children_2_5_couple_woman_only_employed = Column(Float)
    children_2_5_couple_none_employed = Column(Float)

class HouseholdByTerritory(Base):
    """Ménages RP INSEE (DS_RP_MENAGES_COMP / _PRINC) à toutes les échelles — voir migration c5e7a9b1d3f4."""
    __tablename__ = "households_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2012, 2017, 2023
    households = Column(Float)
    household_population = Column(Float)
    one_person = Column(Float)
    men_alone = Column(Float)
    women_alone = Column(Float)
    other_without_family = Column(Float)
    with_family = Column(Float)
    single_parent = Column(Float)
    couple_without_children = Column(Float)
    couple_with_children = Column(Float)
    pcs_1 = Column(Float)
    pcs_2 = Column(Float)
    pcs_3 = Column(Float)
    pcs_4 = Column(Float)
    pcs_5 = Column(Float)
    pcs_6 = Column(Float)
    pcs_7 = Column(Float)
    pcs_9 = Column(Float)
    living_alone_15_24 = Column(Float)
    living_alone_25_39 = Column(Float)
    living_alone_40_54 = Column(Float)
    living_alone_55_64 = Column(Float)
    living_alone_65_79 = Column(Float)
    living_alone_80_plus = Column(Float)
    household_population_15_24 = Column(Float)
    household_population_25_39 = Column(Float)
    household_population_40_54 = Column(Float)
    household_population_55_64 = Column(Float)
    household_population_65_79 = Column(Float)
    household_population_80_plus = Column(Float)

class EducationByTerritory(Base):
    """Scolarisation et diplômes RP INSEE (DS_RP_EDUCATION_PRINC / DS_RP_DIPLOMES_PRINC) — voir migration d6f8b0c2e4a5."""
    __tablename__ = "education_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2012, 2017, 2023
    pop_2_5 = Column(Float)
    enrolled_2_5 = Column(Float)
    pop_6_10 = Column(Float)
    enrolled_6_10 = Column(Float)
    pop_11_14 = Column(Float)
    enrolled_11_14 = Column(Float)
    pop_15_17 = Column(Float)
    enrolled_15_17 = Column(Float)
    pop_18_24 = Column(Float)
    enrolled_18_24 = Column(Float)
    pop_25_29 = Column(Float)
    enrolled_25_29 = Column(Float)
    pop_30_plus = Column(Float)
    enrolled_30_plus = Column(Float)
    pop_15_17_men = Column(Float)
    enrolled_15_17_men = Column(Float)
    pop_15_17_women = Column(Float)
    enrolled_15_17_women = Column(Float)
    pop_18_24_men = Column(Float)
    enrolled_18_24_men = Column(Float)
    pop_18_24_women = Column(Float)
    enrolled_18_24_women = Column(Float)
    non_enrolled_15_plus = Column(Float)
    no_diploma = Column(Float)
    bepc = Column(Float)
    cap_bep = Column(Float)
    bac = Column(Float)
    higher_education = Column(Float)
    bac2 = Column(Float)
    bac3_4 = Column(Float)
    bac5_plus = Column(Float)
    bac3_plus = Column(Float)
    non_enrolled_15_plus_men = Column(Float)
    no_diploma_men = Column(Float)
    higher_education_men = Column(Float)
    non_enrolled_15_plus_women = Column(Float)
    no_diploma_women = Column(Float)
    higher_education_women = Column(Float)
    # Scolarisation à 2 ans et à 3-5 ans (2023 : tableaux détaillés INSEE ; 2017 : agrégat FOR1)
    pop_2 = Column(Float)
    enrolled_2 = Column(Float)
    pop_3_5 = Column(Float)
    enrolled_3_5 = Column(Float)

class EmploymentByTerritory(Base):
    """Emploi, activité, chômage, emplois au lieu de travail et navettes RP INSEE — voir migration f8b0d2e4a6c7."""
    __tablename__ = "employment_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2012, 2017, 2023
    pop_15_64 = Column(Float)
    active_15_64 = Column(Float)
    employed_15_64 = Column(Float)
    unemployed_15_64 = Column(Float)
    pop_15_64_men = Column(Float)
    active_15_64_men = Column(Float)
    employed_15_64_men = Column(Float)
    unemployed_15_64_men = Column(Float)
    pop_15_64_women = Column(Float)
    active_15_64_women = Column(Float)
    employed_15_64_women = Column(Float)
    unemployed_15_64_women = Column(Float)
    pop_15_24 = Column(Float)
    active_15_24 = Column(Float)
    employed_15_24 = Column(Float)
    unemployed_15_24 = Column(Float)
    pop_15_24_men = Column(Float)
    active_15_24_men = Column(Float)
    employed_15_24_men = Column(Float)
    unemployed_15_24_men = Column(Float)
    pop_15_24_women = Column(Float)
    active_15_24_women = Column(Float)
    employed_15_24_women = Column(Float)
    unemployed_15_24_women = Column(Float)
    pop_25_54 = Column(Float)
    active_25_54 = Column(Float)
    employed_25_54 = Column(Float)
    unemployed_25_54 = Column(Float)
    pop_25_54_men = Column(Float)
    active_25_54_men = Column(Float)
    employed_25_54_men = Column(Float)
    unemployed_25_54_men = Column(Float)
    pop_25_54_women = Column(Float)
    active_25_54_women = Column(Float)
    employed_25_54_women = Column(Float)
    unemployed_25_54_women = Column(Float)
    pop_55_64 = Column(Float)
    active_55_64 = Column(Float)
    employed_55_64 = Column(Float)
    unemployed_55_64 = Column(Float)
    pop_55_64_men = Column(Float)
    active_55_64_men = Column(Float)
    employed_55_64_men = Column(Float)
    unemployed_55_64_men = Column(Float)
    pop_55_64_women = Column(Float)
    active_55_64_women = Column(Float)
    employed_55_64_women = Column(Float)
    unemployed_55_64_women = Column(Float)
    retired_15_64 = Column(Float)
    students_15_64 = Column(Float)
    homemakers_15_64 = Column(Float)
    other_inactive_15_64 = Column(Float)
    retired_15_64_men = Column(Float)
    students_15_64_men = Column(Float)
    homemakers_15_64_men = Column(Float)
    other_inactive_15_64_men = Column(Float)
    retired_15_64_women = Column(Float)
    students_15_64_women = Column(Float)
    homemakers_15_64_women = Column(Float)
    other_inactive_15_64_women = Column(Float)
    employed_15_plus = Column(Float)
    active_no_diploma = Column(Float)
    unemployed_no_diploma = Column(Float)
    active_bepc = Column(Float)
    unemployed_bepc = Column(Float)
    active_cap_bep = Column(Float)
    unemployed_cap_bep = Column(Float)
    active_bac = Column(Float)
    unemployed_bac = Column(Float)
    active_bac2 = Column(Float)
    unemployed_bac2 = Column(Float)
    active_bac3_4 = Column(Float)
    unemployed_bac3_4 = Column(Float)
    active_bac5_plus = Column(Float)
    unemployed_bac5_plus = Column(Float)
    active_pcs_1 = Column(Float)
    employed_pcs_1 = Column(Float)
    active_pcs_2 = Column(Float)
    employed_pcs_2 = Column(Float)
    active_pcs_3 = Column(Float)
    employed_pcs_3 = Column(Float)
    active_pcs_4 = Column(Float)
    employed_pcs_4 = Column(Float)
    active_pcs_5 = Column(Float)
    employed_pcs_5 = Column(Float)
    active_pcs_6 = Column(Float)
    employed_pcs_6 = Column(Float)
    jobs = Column(Float)
    jobs_salaried = Column(Float)
    jobs_non_salaried = Column(Float)
    jobs_salaried_part_time = Column(Float)
    jobs_women = Column(Float)
    jobs_agriculture = Column(Float)
    jobs_industry = Column(Float)
    jobs_construction = Column(Float)
    jobs_trade_services = Column(Float)
    jobs_public_services = Column(Float)
    workers = Column(Float)
    work_in_commune = Column(Float)
    work_other_commune_dep = Column(Float)
    work_other_dep_region = Column(Float)
    work_other_region = Column(Float)
    work_abroad_overseas = Column(Float)
    commute_none = Column(Float)
    commute_walk = Column(Float)
    commute_bike = Column(Float)
    commute_two_wheels = Column(Float)
    commute_car = Column(Float)
    commute_public = Column(Float)
    # Actifs occupés résidents : statut, contrat, temps partiel (DS_RP_ACTIVITE_PRINC) — migration b1d3f5a7c9e0
    res_workers = Column(Float)
    res_workers_men = Column(Float)
    res_workers_women = Column(Float)
    res_salaried = Column(Float)
    res_salaried_men = Column(Float)
    res_salaried_women = Column(Float)
    res_non_salaried = Column(Float)
    res_non_salaried_men = Column(Float)
    res_non_salaried_women = Column(Float)
    res_permanent = Column(Float)
    res_permanent_men = Column(Float)
    res_permanent_women = Column(Float)
    res_fixed_term = Column(Float)
    res_fixed_term_men = Column(Float)
    res_fixed_term_women = Column(Float)
    res_part_time = Column(Float)
    res_part_time_men = Column(Float)
    res_part_time_women = Column(Float)
    res_salaried_part_time = Column(Float)
    res_salaried_part_time_men = Column(Float)
    res_salaried_part_time_women = Column(Float)
    res_salaried_15_24 = Column(Float)
    res_salaried_part_time_15_24 = Column(Float)
    res_salaried_15_24_men = Column(Float)
    res_salaried_part_time_15_24_men = Column(Float)
    res_salaried_15_24_women = Column(Float)
    res_salaried_part_time_15_24_women = Column(Float)
    res_salaried_25_54 = Column(Float)
    res_salaried_part_time_25_54 = Column(Float)
    res_salaried_25_54_men = Column(Float)
    res_salaried_part_time_25_54_men = Column(Float)
    res_salaried_25_54_women = Column(Float)
    res_salaried_part_time_25_54_women = Column(Float)
    res_salaried_55_64 = Column(Float)
    res_salaried_part_time_55_64 = Column(Float)
    res_salaried_55_64_men = Column(Float)
    res_salaried_part_time_55_64_men = Column(Float)
    res_salaried_55_64_women = Column(Float)
    res_salaried_part_time_55_64_women = Column(Float)
    res_salaried_15_64 = Column(Float)
    res_salaried_part_time_15_64 = Column(Float)
    res_salaried_15_64_men = Column(Float)
    res_salaried_part_time_15_64_men = Column(Float)
    res_salaried_15_64_women = Column(Float)
    res_salaried_part_time_15_64_women = Column(Float)

class PublicSafety(Base):
    __tablename__ = "public_safety"

    id = Column(Integer, primary_key=True)
    territory_type = Column(String(20), nullable=False, index=True)
    territory_code = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    indicator_class = Column(String(50), nullable=False)
    rate = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Employment(Base):
    __tablename__ = "employment"

    id = Column(Integer, primary_key=True)
    geo_code = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    # Population active féminine
    women_15_64 = Column(Float, nullable=True)
    women_active_15_64 = Column(Float, nullable=True)
    women_employed_15_64 = Column(Float, nullable=True)
    # Temps partiel
    women_employees_25_54 = Column(Float, nullable=True)
    women_part_time_25_54 = Column(Float, nullable=True)
    women_employees_15_64 = Column(Float, nullable=True)
    women_part_time_15_64 = Column(Float, nullable=True)
    # Métadonnées
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Historical(Base):
    __tablename__ = "historical"

    id = Column(Integer, primary_key=True)
    codgeo = Column(String(10), nullable=False, index=True)
    # Recensements
    pop_1968 = Column(Float, nullable=True)
    pop_1975 = Column(Float, nullable=True)
    pop_1982 = Column(Float, nullable=True)
    pop_1990 = Column(Float, nullable=True)
    pop_1999 = Column(Float, nullable=True)
    pop_2010 = Column(Float, nullable=True)
    pop_2015 = Column(Float, nullable=True)
    pop_2021 = Column(Float, nullable=True)
    # Métadonnées
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Revenue(Base):
    __tablename__ = "revenues"

    id = Column(Integer, primary_key=True)
    geo_code = Column(String(10), nullable=False, index=True)
    geo_type = Column(String(10), nullable=False, index=True)  # 'commune', 'epci', 'department', 'region', 'france'
    year = Column(Integer, nullable=False, index=True)
    median_revenue = Column(Float, nullable=True)
    poverty_rate = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Index composite pour accélérer les recherches fréquentes
        Index('ix_revenues_geo_type_geo_code_year', 'geo_type', 'geo_code', 'year'),
    )

class Population(Base):
    __tablename__ = "populations"

    id = Column(Integer, primary_key=True)
    nivgeo = Column(String(10), nullable=False)
    codgeo = Column(String(10), nullable=False, index=True)
    libgeo = Column(String, nullable=False)
    sexe = Column(String(1), nullable=False)
    aged100 = Column(String(3), nullable=False)
    nb = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Index composite pour accélérer les recherches fréquentes
        Index('ix_populations_codgeo_sexe_aged100', 'codgeo', 'sexe', 'aged100'),
    )

class FamilyEmployment(Base):
    __tablename__ = "family_employment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    geo_code = Column(String(10), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    age_group = Column(String(5), nullable=False, index=True)  # "0" pour 0-2 ans, "3" pour 3-5 ans
    tf12 = Column(String(5), nullable=False, index=True)  # Type de famille et situation d'emploi en tant que code
    number = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Index composite pour accélérer les requêtes fréquentes
        Index('ix_family_employment_geo_code_year_age_group_tf12',
              'geo_code', 'year', 'age_group', 'tf12'),
    )

class Childcare(Base):
    __tablename__ = "childcare"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Informations du territoire
    territory_type = Column(String(10), nullable=False, index=True)  # 'commune', 'epci', 'department', 'region', 'france'
    territory_code = Column(String(10), nullable=False, index=True)  # Code du territoire (numcom, numepci, numdep, numregi, 'FR')
    territory_name = Column(String, nullable=True)  # Nom du territoire

    # Année de référence
    year = Column(Integer, nullable=False, index=True)

    # Relations hiérarchiques
    parent_type = Column(String(10), nullable=True)  # Type du territoire parent
    parent_code = Column(String(10), nullable=True)  # Code du territoire parent
    parent_name = Column(String, nullable=True)  # Nom du territoire parent

    # Zone d'emploi (spécifique à certains fichiers)
    employment_zone_code = Column(String(10), nullable=True)  # Code de la zone d'emploi (NUMZEMPL)
    employment_zone_name = Column(String, nullable=True)  # Nom de la zone d'emploi (NOMZEMPL)

    # Taux de couverture par type d'accueil
    # 1. Accueil collectif
    eaje_psu = Column(Float, nullable=True)  # Accueil collectif PSU
    eaje_hors_psu = Column(Float, nullable=True)  # Accueil collectif hors PSU
    eaje_total = Column(Float, nullable=True)  # Total accueil collectif (EAJE)

    # 2. Préscolarisation
    preschool = Column(Float, nullable=True)  # Préscolarisation

    # 3. Accueil individuel
    childminder = Column(Float, nullable=True)  # Assistantes maternelles
    home_care = Column(Float, nullable=True)  # Garde à domicile
    individual_total = Column(Float, nullable=True)  # Total accueil individuel

    # 4. Taux global
    global_rate = Column(Float, nullable=True)  # Couverture globale

    # Source des données
    data_source = Column(String(50), nullable=True)  # 'csv_2020', 'csv_2021', 'parquet', etc.

    # Métadonnées
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Index composites pour optimiser les requêtes
        Index('ix_childcare_territory_type_code_year', 'territory_type', 'territory_code', 'year'),
        Index('ix_childcare_parent_type_code', 'parent_type', 'parent_code'),
    )

class IrisPopulation(Base):
    __tablename__ = "iris_population"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    iris_code = Column(String(9),   nullable=False)
    com_code  = Column(String(5),   nullable=False)
    iris_name = Column(String(255), nullable=True)   # LIBIRIS
    dep_code  = Column(String(3),   nullable=True)   # DEP
    reg_code  = Column(String(2),   nullable=True)   # REG
    year      = Column(Integer,     nullable=False)

    pop          = Column(Float, nullable=True)
    pop_0_2      = Column(Float, nullable=True)
    pop_3_5      = Column(Float, nullable=True)
    pop_6_10     = Column(Float, nullable=True)
    pop_11_17    = Column(Float, nullable=True)
    pop_18_24    = Column(Float, nullable=True)
    pop_25_39    = Column(Float, nullable=True)
    pop_40_54    = Column(Float, nullable=True)
    pop_55_64    = Column(Float, nullable=True)
    pop_65_79    = Column(Float, nullable=True)
    pop_80_plus  = Column(Float, nullable=True)
    pop_foreign   = Column(Float, nullable=True)
    pop_immigrant = Column(Float, nullable=True)
    pop_women = Column(Float, nullable=True)
    pop_men   = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("iris_code", "year", name="uq_iris_population_iris_year"),
        Index("ix_iris_population_iris_year", "iris_code", "year"),
        Index("ix_iris_population_com_year",  "com_code",  "year"),
        Index("ix_iris_population_dep_code",  "dep_code"),
        Index("ix_iris_population_reg_code",  "reg_code"),
        Index("ix_iris_population_year",      "year"),
    )

class IrisFamilies(Base):
    __tablename__ = "iris_families"

    id        = Column(Integer,     primary_key=True, autoincrement=True)
    iris_code = Column(String(9),   nullable=False)
    com_code  = Column(String(5),   nullable=False)
    iris_name = Column(String(255), nullable=True)
    dep_code  = Column(String(3),   nullable=True)
    reg_code  = Column(String(2),   nullable=True)
    year      = Column(Integer,     nullable=False)

    # Population 15 ans ou plus
    pop_15p         = Column(Float, nullable=True)   # P22_POP15P
    pop_15_24       = Column(Float, nullable=True)   # P22_POP1524
    pop_25_54       = Column(Float, nullable=True)   # P22_POP2554
    pop_55_79       = Column(Float, nullable=True)   # P22_POP5579
    pop_80p         = Column(Float, nullable=True)   # P22_POP80P
    # Personnes vivant seules
    pop_15p_alone   = Column(Float, nullable=True)   # P22_POP15P_PSEUL
    pop_15_24_alone = Column(Float, nullable=True)   # P22_POP1524_PSEUL
    pop_25_54_alone = Column(Float, nullable=True)   # P22_POP2554_PSEUL
    pop_55_79_alone = Column(Float, nullable=True)   # P22_POP5579_PSEUL
    pop_80p_alone   = Column(Float, nullable=True)   # P22_POP80P_PSEUL
    # Familles
    families             = Column(Float, nullable=True)  # C22_FAM
    couples_with_children = Column(Float, nullable=True) # C22_COUPAENF
    single_parent        = Column(Float, nullable=True)  # C22_FAMMONO
    couples_no_children  = Column(Float, nullable=True)  # C22_COUPSENF
    # Nombre d'enfants
    families_0_children  = Column(Float, nullable=True)  # C22_NE24F0
    families_1_child     = Column(Float, nullable=True)  # C22_NE24F1
    families_2_children  = Column(Float, nullable=True)  # C22_NE24F2
    families_3_children  = Column(Float, nullable=True)  # C22_NE24F3
    families_4p_children = Column(Float, nullable=True)  # C22_NE24F4P

    __table_args__ = (
        UniqueConstraint("iris_code", "year", name="uq_iris_families_iris_year"),
        Index("ix_iris_families_iris_year", "iris_code", "year"),
        Index("ix_iris_families_com_year",  "com_code",  "year"),
        Index("ix_iris_families_dep_code",  "dep_code"),
        Index("ix_iris_families_reg_code",  "reg_code"),
        Index("ix_iris_families_year",      "year"),
    )

# ── À ajouter dans app/models.py ──────────────────────────────────────────────

class IrisHousing(Base):
    __tablename__ = "iris_housing"

    id        = Column(Integer,     primary_key=True, autoincrement=True)
    iris_code = Column(String(9),   nullable=False)
    com_code  = Column(String(5),   nullable=False)
    iris_name = Column(String(255), nullable=True)
    dep_code  = Column(String(3),   nullable=True)
    reg_code  = Column(String(2),   nullable=True)
    year      = Column(Integer,     nullable=False)

    # Logements
    housing_total       = Column(Float, nullable=True)  # P22_LOG
    main_res            = Column(Float, nullable=True)  # P22_RP
    second_res          = Column(Float, nullable=True)  # P22_RSECOCC
    vacant              = Column(Float, nullable=True)  # P22_LOGVAC
    houses              = Column(Float, nullable=True)  # P22_MAISON
    apartments          = Column(Float, nullable=True)  # P22_APPART
    # Résidences principales par nombre de pièces
    rp_1room            = Column(Float, nullable=True)  # P22_RP_1P
    rp_2rooms           = Column(Float, nullable=True)  # P22_RP_2P
    rp_3rooms           = Column(Float, nullable=True)  # P22_RP_3P
    rp_4rooms           = Column(Float, nullable=True)  # P22_RP_4P
    rp_5p_rooms         = Column(Float, nullable=True)  # P22_RP_5PP
    # Résidences principales par surface
    rp_u30m2            = Column(Float, nullable=True)  # P22_RP_M30M2
    rp_30_40m2          = Column(Float, nullable=True)  # P22_RP_3040M2
    rp_40_60m2          = Column(Float, nullable=True)  # P22_RP_4060M2
    rp_60_80m2          = Column(Float, nullable=True)  # P22_RP_6080M2
    rp_80_100m2         = Column(Float, nullable=True)  # P22_RP_80100M2
    rp_100_120m2        = Column(Float, nullable=True)  # P22_RP_100120M2
    rp_120p_m2          = Column(Float, nullable=True)  # P22_RP_120M2P
    # Résidences principales par période de construction
    rp_built_pre1919    = Column(Float, nullable=True)  # P22_RP_ACH1919
    rp_built_1919_1945  = Column(Float, nullable=True)  # P22_RP_ACH1945
    rp_built_1946_1970  = Column(Float, nullable=True)  # P22_RP_ACH1970
    rp_built_1971_1990  = Column(Float, nullable=True)  # P22_RP_ACH1990
    rp_built_1991_2005  = Column(Float, nullable=True)  # P22_RP_ACH2005
    rp_built_2006_2019  = Column(Float, nullable=True)  # P22_RP_ACH2019
    # Ménages
    households          = Column(Float, nullable=True)  # P22_MEN
    hh_moved_u2y        = Column(Float, nullable=True)  # P22_MEN_ANEM0002
    hh_moved_2_4y       = Column(Float, nullable=True)  # P22_MEN_ANEM0204
    hh_moved_5_9y       = Column(Float, nullable=True)  # P22_MEN_ANEM0509
    hh_moved_10py       = Column(Float, nullable=True)  # P22_MEN_ANEM10P
    # Statut d'occupation
    rp_owners           = Column(Float, nullable=True)  # P22_RP_PROP
    rp_renters          = Column(Float, nullable=True)  # P22_RP_LOC
    rp_social_housing   = Column(Float, nullable=True)  # P22_RP_LOCHLMV
    rp_free             = Column(Float, nullable=True)  # P22_RP_GRAT
    # Chauffage
    heat_gas_network    = Column(Float, nullable=True)  # P22_RP_CGAZV
    heat_fuel           = Column(Float, nullable=True)  # P22_RP_CFIOUL
    heat_electric       = Column(Float, nullable=True)  # P22_RP_CELEC
    heat_gas_bottle     = Column(Float, nullable=True)  # P22_RP_CGAZB
    heat_other          = Column(Float, nullable=True)  # P22_RP_CAUT
    # Voitures
    hh_1p_car           = Column(Float, nullable=True)  # P22_RP_VOIT1P
    hh_1_car            = Column(Float, nullable=True)  # P22_RP_VOIT1
    hh_2p_cars          = Column(Float, nullable=True)  # P22_RP_VOIT2P
    # Occupation
    rp_standard_occ     = Column(Float, nullable=True)  # C22_RP_NORME
    rp_mild_underuse    = Column(Float, nullable=True)  # C22_RP_SOUSOCC_MOD
    rp_heavy_underuse   = Column(Float, nullable=True)  # C22_RP_SOUSOCC_ACC
    rp_extreme_underuse = Column(Float, nullable=True)  # C22_RP_SOUSOCC_TACC
    rp_mild_overuse     = Column(Float, nullable=True)  # C22_RP_SUROCC_MOD
    rp_heavy_overuse    = Column(Float, nullable=True)  # C22_RP_SUROCC_ACC

    __table_args__ = (
        UniqueConstraint("iris_code", "year", name="uq_iris_housing_iris_year"),
        Index("ix_iris_housing_iris_year", "iris_code", "year"),
        Index("ix_iris_housing_com_year",  "com_code",  "year"),
        Index("ix_iris_housing_dep_code",  "dep_code"),
        Index("ix_iris_housing_reg_code",  "reg_code"),
        Index("ix_iris_housing_year",      "year"),
    )

# ── À ajouter dans app/models.py ──────────────────────────────────────────────

class IrisEducation(Base):
    __tablename__ = "iris_education"

    id        = Column(Integer,     primary_key=True, autoincrement=True)
    iris_code = Column(String(9),   nullable=False)
    com_code  = Column(String(5),   nullable=False)
    iris_name = Column(String(255), nullable=True)
    dep_code  = Column(String(3),   nullable=True)
    reg_code  = Column(String(2),   nullable=True)
    year      = Column(Integer,     nullable=False)

    # Population par tranche d'âge
    pop_2_5   = Column(Float, nullable=True)   # P22_POP0205
    pop_6_10  = Column(Float, nullable=True)   # P22_POP0610
    pop_11_14 = Column(Float, nullable=True)   # P22_POP1114
    pop_15_17 = Column(Float, nullable=True)   # P22_POP1517
    pop_18_24 = Column(Float, nullable=True)   # P22_POP1824
    pop_25_29 = Column(Float, nullable=True)   # P22_POP2529
    pop_30p   = Column(Float, nullable=True)   # P22_POP30P
    # Scolarisés
    scol_2_5   = Column(Float, nullable=True)  # P22_SCOL0205
    scol_6_10  = Column(Float, nullable=True)  # P22_SCOL0610
    scol_11_14 = Column(Float, nullable=True)  # P22_SCOL1114
    scol_15_17 = Column(Float, nullable=True)  # P22_SCOL1517
    scol_18_24 = Column(Float, nullable=True)  # P22_SCOL1824
    scol_25_29 = Column(Float, nullable=True)  # P22_SCOL2529
    scol_30p   = Column(Float, nullable=True)  # P22_SCOL30P
    # Non scolarisés 15+ — Total
    nscol_15p         = Column(Float, nullable=True)  # P22_NSCOL15P
    nscol_15p_no_dip  = Column(Float, nullable=True)  # P22_NSCOL15P_DIPLMIN
    nscol_15p_bepc    = Column(Float, nullable=True)  # P22_NSCOL15P_BEPC
    nscol_15p_capbep  = Column(Float, nullable=True)  # P22_NSCOL15P_CAPBEP
    nscol_15p_bac     = Column(Float, nullable=True)  # P22_NSCOL15P_BAC
    nscol_15p_sup2    = Column(Float, nullable=True)  # P22_NSCOL15P_SUP2
    nscol_15p_sup34   = Column(Float, nullable=True)  # P22_NSCOL15P_SUP34
    nscol_15p_sup5    = Column(Float, nullable=True)  # P22_NSCOL15P_SUP5
    # Non scolarisés 15+ — Hommes
    nscol_15p_men         = Column(Float, nullable=True)  # P22_HNSCOL15P
    nscol_15p_men_no_dip  = Column(Float, nullable=True)  # P22_HNSCOL15P_DIPLMIN
    nscol_15p_men_bepc    = Column(Float, nullable=True)  # P22_HNSCOL15P_BEPC
    nscol_15p_men_capbep  = Column(Float, nullable=True)  # P22_HNSCOL15P_CAPBEP
    nscol_15p_men_bac     = Column(Float, nullable=True)  # P22_HNSCOL15P_BAC
    nscol_15p_men_sup2    = Column(Float, nullable=True)  # P22_HNSCOL15P_SUP2
    nscol_15p_men_sup34   = Column(Float, nullable=True)  # P22_HNSCOL15P_SUP34
    nscol_15p_men_sup5    = Column(Float, nullable=True)  # P22_HNSCOL15P_SUP5
    # Non scolarisés 15+ — Femmes
    nscol_15p_women         = Column(Float, nullable=True)  # P22_FNSCOL15P
    nscol_15p_women_no_dip  = Column(Float, nullable=True)  # P22_FNSCOL15P_DIPLMIN
    nscol_15p_women_bepc    = Column(Float, nullable=True)  # P22_FNSCOL15P_BEPC
    nscol_15p_women_capbep  = Column(Float, nullable=True)  # P22_FNSCOL15P_CAPBEP
    nscol_15p_women_bac     = Column(Float, nullable=True)  # P22_FNSCOL15P_BAC
    nscol_15p_women_sup2    = Column(Float, nullable=True)  # P22_FNSCOL15P_SUP2
    nscol_15p_women_sup34   = Column(Float, nullable=True)  # P22_FNSCOL15P_SUP34
    nscol_15p_women_sup5    = Column(Float, nullable=True)  # P22_FNSCOL15P_SUP5

    __table_args__ = (
        UniqueConstraint("iris_code", "year", name="uq_iris_education_iris_year"),
        Index("ix_iris_education_iris_year", "iris_code", "year"),
        Index("ix_iris_education_com_year",  "com_code",  "year"),
        Index("ix_iris_education_dep_code",  "dep_code"),
        Index("ix_iris_education_reg_code",  "reg_code"),
        Index("ix_iris_education_year",      "year"),
    )

# ── À ajouter dans app/models.py ──────────────────────────────────────────────

class IrisActivity(Base):
    __tablename__ = "iris_activity"

    id        = Column(Integer,     primary_key=True, autoincrement=True)
    iris_code = Column(String(9),   nullable=False)
    com_code  = Column(String(5),   nullable=False)
    iris_name = Column(String(255), nullable=True)
    dep_code  = Column(String(3),   nullable=True)
    reg_code  = Column(String(2),   nullable=True)
    year      = Column(Integer,     nullable=False)

    # Population 15-64 ans — Total
    pop_15_64  = Column(Float, nullable=True)   # P22_POP1564
    pop_15_24  = Column(Float, nullable=True)   # P22_POP1524
    pop_25_54  = Column(Float, nullable=True)   # P22_POP2554
    pop_55_64  = Column(Float, nullable=True)   # P22_POP5564
    # Population 15-64 ans — Hommes
    pop_men_15_64 = Column(Float, nullable=True)  # P22_H1564
    pop_men_15_24 = Column(Float, nullable=True)  # P22_H1524
    pop_men_25_54 = Column(Float, nullable=True)  # P22_H2554
    pop_men_55_64 = Column(Float, nullable=True)  # P22_H5564
    # Population 15-64 ans — Femmes
    pop_women_15_64 = Column(Float, nullable=True)  # P22_F1564
    pop_women_15_24 = Column(Float, nullable=True)  # P22_F1524
    pop_women_25_54 = Column(Float, nullable=True)  # P22_F2554
    pop_women_55_64 = Column(Float, nullable=True)  # P22_F5564
    # Actifs — Total
    active_15_64 = Column(Float, nullable=True)  # P22_ACT1564
    active_15_24 = Column(Float, nullable=True)  # P22_ACT1524
    active_25_54 = Column(Float, nullable=True)  # P22_ACT2554
    active_55_64 = Column(Float, nullable=True)  # P22_ACT5564
    # Actifs — Hommes
    active_men_15_64 = Column(Float, nullable=True)  # P22_HACT1564
    active_men_15_24 = Column(Float, nullable=True)  # P22_HACT1524
    active_men_25_54 = Column(Float, nullable=True)  # P22_HACT2554
    active_men_55_64 = Column(Float, nullable=True)  # P22_HACT5564
    # Actifs — Femmes
    active_women_15_64 = Column(Float, nullable=True)  # P22_FACT1564
    active_women_15_24 = Column(Float, nullable=True)  # P22_FACT1524
    active_women_25_54 = Column(Float, nullable=True)  # P22_FACT2554
    active_women_55_64 = Column(Float, nullable=True)  # P22_FACT5564
    # Actifs occupés — Total
    employed_15_64 = Column(Float, nullable=True)  # P22_ACTOCC1564
    employed_15_24 = Column(Float, nullable=True)  # P22_ACTOCC1524
    employed_25_54 = Column(Float, nullable=True)  # P22_ACTOCC2554
    employed_55_64 = Column(Float, nullable=True)  # P22_ACTOCC5564
    # Actifs occupés — Hommes
    employed_men_15_64 = Column(Float, nullable=True)  # P22_HACTOCC1564
    employed_men_15_24 = Column(Float, nullable=True)  # P22_HACTOCC1524
    employed_men_25_54 = Column(Float, nullable=True)  # P22_HACTOCC2554
    employed_men_55_64 = Column(Float, nullable=True)  # P22_HACTOCC5564
    # Actifs occupés — Femmes
    employed_women_15_64 = Column(Float, nullable=True)  # P22_FACTOCC1564
    employed_women_15_24 = Column(Float, nullable=True)  # P22_FACTOCC1524
    employed_women_25_54 = Column(Float, nullable=True)  # P22_FACTOCC2554
    employed_women_55_64 = Column(Float, nullable=True)  # P22_FACTOCC5564
    # Chômeurs par tranche d'âge
    unemp_15_64 = Column(Float, nullable=True)  # P22_CHOM1564
    unemp_15_24 = Column(Float, nullable=True)  # P22_CHOM1524
    unemp_25_54 = Column(Float, nullable=True)  # P22_CHOM2554
    unemp_55_64 = Column(Float, nullable=True)  # P22_CHOM5564
    # Actifs par diplôme
    active_no_dip = Column(Float, nullable=True)  # P22_ACT_DIPLMIN
    active_bepc   = Column(Float, nullable=True)  # P22_ACT_BEPC
    active_capbep = Column(Float, nullable=True)  # P22_ACT_CAPBEP
    active_bac    = Column(Float, nullable=True)  # P22_ACT_BAC
    active_sup2   = Column(Float, nullable=True)  # P22_ACT_SUP2
    active_sup34  = Column(Float, nullable=True)  # P22_ACT_SUP34
    active_sup5   = Column(Float, nullable=True)  # P22_ACT_SUP5
    # Chômeurs par diplôme
    unemp_no_dip  = Column(Float, nullable=True)  # P22_CHOM_DIPLMIN
    unemp_bepc    = Column(Float, nullable=True)  # P22_CHOM_BEPC
    unemp_capbep  = Column(Float, nullable=True)  # P22_CHOM_CAPBEP
    unemp_bac     = Column(Float, nullable=True)  # P22_CHOM_BAC
    unemp_sup2    = Column(Float, nullable=True)  # P22_CHOM_SUP2
    unemp_sup34   = Column(Float, nullable=True)  # P22_CHOM_SUP34
    unemp_sup5    = Column(Float, nullable=True)  # P22_CHOM_SUP5
    # Inactifs
    inactive_15_64       = Column(Float, nullable=True)  # P22_INACT1564
    inactive_men_15_64   = Column(Float, nullable=True)  # P22_HINACT1564
    inactive_women_15_64 = Column(Float, nullable=True)  # P22_FINACT1564
    student_15_64        = Column(Float, nullable=True)  # P22_ETUD1564
    student_men_15_64    = Column(Float, nullable=True)  # P22_HETUD1564
    student_women_15_64  = Column(Float, nullable=True)  # P22_FETUD1564
    retired_15_64        = Column(Float, nullable=True)  # P22_RETR1564
    retired_men_15_64    = Column(Float, nullable=True)  # P22_HRETR1564
    retired_women_15_64  = Column(Float, nullable=True)  # P22_FRETR1564
    other_inactive_15_64       = Column(Float, nullable=True)  # P22_AINACT1564
    other_inactive_men_15_64   = Column(Float, nullable=True)  # P22_HAINACT1564
    other_inactive_women_15_64 = Column(Float, nullable=True)  # P22_FAINACT1564
    # Actifs par CSP (compl)
    act_farmers      = Column(Float, nullable=True)  # C22_ACT1564_STAT_GSEC11_21
    act_craftsmen    = Column(Float, nullable=True)  # C22_ACT1564_STAT_GSEC12_22
    act_executives   = Column(Float, nullable=True)  # C22_ACT1564_STAT_GSEC13_23
    act_intermediary = Column(Float, nullable=True)  # C22_ACT1564_STAT_GSEC14_24
    act_employees    = Column(Float, nullable=True)  # C22_ACT1564_STAT_GSEC15_25
    act_workers      = Column(Float, nullable=True)  # C22_ACT1564_STAT_GSEC16_26
    emp_farmers      = Column(Float, nullable=True)  # C22_ACTOCC1564_STAT_GSEC11
    emp_craftsmen    = Column(Float, nullable=True)  # C22_ACTOCC1564_STAT_GSEC12
    emp_executives   = Column(Float, nullable=True)  # C22_ACTOCC1564_STAT_GSEC13
    emp_intermediary = Column(Float, nullable=True)  # C22_ACTOCC1564_STAT_GSEC14
    emp_employees    = Column(Float, nullable=True)  # C22_ACTOCC1564_STAT_GSEC15
    emp_workers      = Column(Float, nullable=True)  # C22_ACTOCC1564_STAT_GSEC16
    # Actifs occupés 15+
    employed_15p       = Column(Float, nullable=True)  # P22_ACTOCC15P
    employed_men_15p   = Column(Float, nullable=True)  # P22_HACTOCC15P
    employed_women_15p = Column(Float, nullable=True)  # P22_FACTOCC15P
    # Salariés / Non-salariés
    salaried_15p       = Column(Float, nullable=True)  # P22_SAL15P
    salaried_men_15p   = Column(Float, nullable=True)  # P22_HSAL15P
    salaried_women_15p = Column(Float, nullable=True)  # P22_FSAL15P
    self_emp_15p       = Column(Float, nullable=True)  # P22_NSAL15P
    self_emp_men_15p   = Column(Float, nullable=True)  # P22_HNSAL15P
    self_emp_women_15p = Column(Float, nullable=True)  # P22_FNSAL15P
    # Temps partiel
    employed_15p_pt   = Column(Float, nullable=True)  # P22_ACTOCC15P_TP
    salaried_15p_pt   = Column(Float, nullable=True)  # P22_SAL15P_TP
    salaried_men_pt   = Column(Float, nullable=True)  # P22_HSAL15P_TP
    salaried_women_pt = Column(Float, nullable=True)  # P22_FSAL15P_TP
    self_emp_15p_pt   = Column(Float, nullable=True)  # P22_NSAL15P_TP
    # Type de contrat
    sal_cdi     = Column(Float, nullable=True)  # P22_SAL15P_CDI
    sal_cdd     = Column(Float, nullable=True)  # P22_SAL15P_CDD
    sal_interim = Column(Float, nullable=True)  # P22_SAL15P_INTERIM
    sal_aided   = Column(Float, nullable=True)  # P22_SAL15P_EMPAID
    sal_appr    = Column(Float, nullable=True)  # P22_SAL15P_APPR
    # Non-salariés par type
    self_emp_indep  = Column(Float, nullable=True)  # P22_NSAL15P_INDEP
    self_emp_employ = Column(Float, nullable=True)  # P22_NSAL15P_EMPLOY
    self_emp_family = Column(Float, nullable=True)  # P22_NSAL15P_AIDFAM
    # Lieu de travail
    work_same_commune       = Column(Float, nullable=True)  # P22_ACTOCC15P_ILT1
    work_other_commune      = Column(Float, nullable=True)  # P22_ACTOCC15P_ILT2P
    work_other_dep_same_reg = Column(Float, nullable=True)  # P22_ACTOCC15P_ILT3
    work_other_reg_metro    = Column(Float, nullable=True)  # P22_ACTOCC15P_ILT4
    work_other_reg_domtom   = Column(Float, nullable=True)  # P22_ACTOCC15P_ILT5
    # Mode de transport (compl)
    transport_none    = Column(Float, nullable=True)  # C22_ACTOCC15P_PAS
    transport_walk    = Column(Float, nullable=True)  # C22_ACTOCC15P_MAR
    transport_bike    = Column(Float, nullable=True)  # C22_ACTOCC15P_VELO
    transport_moto    = Column(Float, nullable=True)  # C22_ACTOCC15P_2ROUESMOT
    transport_car     = Column(Float, nullable=True)  # C22_ACTOCC15P_VOIT
    transport_transit = Column(Float, nullable=True)  # C22_ACTOCC15P_TCOM

    __table_args__ = (
        UniqueConstraint("iris_code", "year", name="uq_iris_activity_iris_year"),
        Index("ix_iris_activity_iris_year", "iris_code", "year"),
        Index("ix_iris_activity_com_year",  "com_code",  "year"),
        Index("ix_iris_activity_dep_code",  "dep_code"),
        Index("ix_iris_activity_reg_code",  "reg_code"),
        Index("ix_iris_activity_year",      "year"),
    )


class HousingByTerritory(Base):
    """Logement RP INSEE (DS_RP_LOGEMENT_PRINC / _COMP) à toutes les échelles — voir migration c2e4f6a8b0d1."""
    __tablename__ = "housing_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2012, 2017, 2023
    dwellings = Column(Float)
    dwellings_main = Column(Float)
    dwellings_secondary = Column(Float)
    dwellings_vacant = Column(Float)
    dwellings_houses = Column(Float)
    dwellings_apartments = Column(Float)
    main_houses = Column(Float)
    main_apartments = Column(Float)
    main_r1 = Column(Float)
    main_r2 = Column(Float)
    main_r3 = Column(Float)
    main_r4 = Column(Float)
    main_r5p = Column(Float)
    main_rooms = Column(Float)
    main_owners = Column(Float)
    main_tenants = Column(Float)
    main_tenants_private = Column(Float)
    main_tenants_furnished = Column(Float)
    main_tenants_social = Column(Float)
    main_free = Column(Float)
    pop_main = Column(Float)
    pop_owners = Column(Float)
    pop_tenants = Column(Float)
    pop_tenants_social = Column(Float)
    stay_lt2 = Column(Float)
    stay_2_4 = Column(Float)
    stay_5_9 = Column(Float)
    stay_10_19 = Column(Float)
    stay_20_29 = Column(Float)
    stay_ge30 = Column(Float)
    stay_years = Column(Float)
    stay_years_owners = Column(Float)
    stay_years_tenants = Column(Float)
    stay_years_social = Column(Float)
    heat_town_gas = Column(Float)
    heat_oil = Column(Float)
    heat_electric = Column(Float)
    heat_bottled_gas = Column(Float)
    heat_other = Column(Float)
    with_parking = Column(Float)
    cars_0 = Column(Float)
    cars_1 = Column(Float)
    cars_2p = Column(Float)
    built_lt1919 = Column(Float)
    built_1919_1945 = Column(Float)
    built_1946_1970 = Column(Float)
    built_1971_1990 = Column(Float)
    built_1991_2005 = Column(Float)
    built_2006_plus = Column(Float)
    occ_total = Column(Float)
    occ_over_severe = Column(Float)
    occ_over_moderate = Column(Float)
    occ_standard = Column(Float)
    occ_under_moderate = Column(Float)
    occ_under_severe = Column(Float)
    occ_under_very_severe = Column(Float)
    built_before_1946 = Column(Float)
    built_1946_1990 = Column(Float)
    built_after_1990 = Column(Float)
    built_known = Column(Float)


class PopulationByTerritory(Base):
    """Population RP INSEE (âges, pyramide, PCS, mobilité) — voir migration d3f5a7b9c1e2."""
    __tablename__ = "population_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2012, 2017, 2023
    pop = Column(Float)
    pop_women = Column(Float)
    pop_men = Column(Float)
    pop_lt15 = Column(Float)
    pop_lt15_women = Column(Float)
    pop_lt15_men = Column(Float)
    pop_15_24 = Column(Float)
    pop_15_24_women = Column(Float)
    pop_15_24_men = Column(Float)
    pop_25_39 = Column(Float)
    pop_25_39_women = Column(Float)
    pop_25_39_men = Column(Float)
    pop_40_54 = Column(Float)
    pop_40_54_women = Column(Float)
    pop_40_54_men = Column(Float)
    pop_55_64 = Column(Float)
    pop_55_64_women = Column(Float)
    pop_55_64_men = Column(Float)
    pop_65_79 = Column(Float)
    pop_65_79_women = Column(Float)
    pop_65_79_men = Column(Float)
    pop_ge80 = Column(Float)
    pop_ge80_women = Column(Float)
    pop_ge80_men = Column(Float)
    pop_ge65 = Column(Float)
    pop_ge65_women = Column(Float)
    pop_ge65_men = Column(Float)
    pop_lt20 = Column(Float)
    pop_lt20_women = Column(Float)
    pop_lt20_men = Column(Float)
    pop_20_64 = Column(Float)
    pop_20_64_women = Column(Float)
    pop_20_64_men = Column(Float)
    pop_15p = Column(Float)
    pcs_1 = Column(Float)
    pcs_2 = Column(Float)
    pcs_3 = Column(Float)
    pcs_4 = Column(Float)
    pcs_5 = Column(Float)
    pcs_6 = Column(Float)
    pcs_7 = Column(Float)
    pcs_9 = Column(Float)
    mig_total = Column(Float)
    mig_same_dwelling = Column(Float)
    mig_same_commune = Column(Float)
    mig_other_commune = Column(Float)
    mig_same_department = Column(Float)
    mig_same_region = Column(Float)
    mig_other_region = Column(Float)
    mig_overseas = Column(Float)
    mig_abroad = Column(Float)
    mig_other_commune_1_14 = Column(Float)
    mig_other_commune_15_24 = Column(Float)
    mig_other_commune_25_54 = Column(Float)
    mig_other_commune_ge55 = Column(Float)
    pyr_men_0_4 = Column(Float)
    pyr_women_0_4 = Column(Float)
    pyr_men_5_9 = Column(Float)
    pyr_women_5_9 = Column(Float)
    pyr_men_10_14 = Column(Float)
    pyr_women_10_14 = Column(Float)
    pyr_men_15_19 = Column(Float)
    pyr_women_15_19 = Column(Float)
    pyr_men_20_24 = Column(Float)
    pyr_women_20_24 = Column(Float)
    pyr_men_25_29 = Column(Float)
    pyr_women_25_29 = Column(Float)
    pyr_men_30_34 = Column(Float)
    pyr_women_30_34 = Column(Float)
    pyr_men_35_39 = Column(Float)
    pyr_women_35_39 = Column(Float)
    pyr_men_40_44 = Column(Float)
    pyr_women_40_44 = Column(Float)
    pyr_men_45_49 = Column(Float)
    pyr_women_45_49 = Column(Float)
    pyr_men_50_54 = Column(Float)
    pyr_women_50_54 = Column(Float)
    pyr_men_55_59 = Column(Float)
    pyr_women_55_59 = Column(Float)
    pyr_men_60_64 = Column(Float)
    pyr_women_60_64 = Column(Float)
    pyr_men_65_69 = Column(Float)
    pyr_women_65_69 = Column(Float)
    pyr_men_70_74 = Column(Float)
    pyr_women_70_74 = Column(Float)
    pyr_men_75_79 = Column(Float)
    pyr_women_75_79 = Column(Float)
    pyr_men_80_84 = Column(Float)
    pyr_women_80_84 = Column(Float)
    pyr_men_85_89 = Column(Float)
    pyr_women_85_89 = Column(Float)
    pyr_men_90_94 = Column(Float)
    pyr_women_90_94 = Column(Float)
    pyr_men_ge95 = Column(Float)
    pyr_women_ge95 = Column(Float)
    age_0_2 = Column(Float)
    age_3_5 = Column(Float)
    age_6_10 = Column(Float)
    age_11_14 = Column(Float)
    age_15_17 = Column(Float)
    age_18_24 = Column(Float)


class PopulationHistoryByTerritory(Base):
    """Série historique RP INSEE 1968-2023 — voir migration d3f5a7b9c1e2."""
    __tablename__ = "population_history_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 1968, 1975, ..., 2017, 2023
    population = Column(Float)
    births = Column(Float)
    deaths = Column(Float)
    dwellings = Column(Float)
    dwellings_main = Column(Float)
    dwellings_secondary = Column(Float)
    dwellings_vacant = Column(Float)
    households_population = Column(Float)
    area_km2 = Column(Float)


class ChildcareByTerritory(Base):
    """Accueil du jeune enfant (Cnaf) : places et taux de couverture par mode — voir migration e4a6c8d0f2b3."""
    __tablename__ = "childcare_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FE' (France entière hors Mayotte)
    year = Column(Integer, primary_key=True)           # 2017 à 2023
    places_eaje_psu = Column(Float)
    places_eaje_hors_psu = Column(Float)
    places_eaje = Column(Float)
    places_preschool = Column(Float)
    places_childminder = Column(Float)
    places_home_care = Column(Float)
    places_individual = Column(Float)
    places_total = Column(Float)
    rate_eaje_psu = Column(Float)
    rate_eaje_hors_psu = Column(Float)
    rate_eaje = Column(Float)
    rate_preschool = Column(Float)
    rate_childminder = Column(Float)
    rate_home_care = Column(Float)
    rate_individual = Column(Float)
    rate_global = Column(Float)
    source = Column(String(20))                        # cnaf_detail | cnaf_tauxcouv


class CafBenefitsByTerritory(Base):
    """Prestations CAF (Cnaf) : foyers allocataires, personnes couvertes, montants — voir migration f5b7d9e1a3c4."""
    __tablename__ = "caf_benefits_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole, somme des départements)
    year = Column(Integer, primary_key=True)           # 2020 à 2024 (31 décembre)
    all_households = Column(Float)
    all_persons = Column(Float)
    all_amount = Column(Float)
    paje_households = Column(Float)
    paje_persons = Column(Float)
    paje_amount = Column(Float)
    paje_basic_households = Column(Float)
    paje_basic_persons = Column(Float)
    paje_basic_amount = Column(Float)
    cmg_households = Column(Float)
    cmg_persons = Column(Float)
    cmg_amount = Column(Float)
    prepare_households = Column(Float)
    prepare_persons = Column(Float)
    prepare_amount = Column(Float)
    children_households = Column(Float)
    children_persons = Column(Float)
    children_amount = Column(Float)
    af_households = Column(Float)
    af_persons = Column(Float)
    af_amount = Column(Float)
    cf_households = Column(Float)
    cf_persons = Column(Float)
    cf_amount = Column(Float)
    ars_households = Column(Float)
    ars_persons = Column(Float)
    ars_amount = Column(Float)
    asf_households = Column(Float)
    asf_persons = Column(Float)
    asf_amount = Column(Float)
    disability_households = Column(Float)
    disability_persons = Column(Float)
    disability_amount = Column(Float)
    aah_households = Column(Float)
    aah_persons = Column(Float)
    aah_amount = Column(Float)
    aeeh_households = Column(Float)
    aeeh_persons = Column(Float)
    aeeh_amount = Column(Float)
    housing_households = Column(Float)
    housing_persons = Column(Float)
    housing_amount = Column(Float)
    apl_households = Column(Float)
    apl_persons = Column(Float)
    apl_amount = Column(Float)
    alf_households = Column(Float)
    alf_persons = Column(Float)
    alf_amount = Column(Float)
    als_households = Column(Float)
    als_persons = Column(Float)
    als_amount = Column(Float)
    insertion_households = Column(Float)
    insertion_persons = Column(Float)
    insertion_amount = Column(Float)
    rsa_households = Column(Float)
    rsa_persons = Column(Float)
    rsa_amount = Column(Float)
    ppa_households = Column(Float)
    ppa_persons = Column(Float)
    ppa_amount = Column(Float)
    aah_beneficiaries = Column(Float)
    aeeh_beneficiaries = Column(Float)


class RevenuesByTerritory(Base):
    """Revenus et pauvreté (INSEE, Filosofi 2017-2021 et 2023) — voir migration a6c8e0f2b4d5."""
    __tablename__ = "revenues_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2017 à 2021, 2023
    fiscal_households = Column(Float)
    fiscal_persons = Column(Float)
    median_living_standard = Column(Float)
    taxed_households_rate = Column(Float)
    poverty_rate = Column(Float)
    poverty_rate_ref_lt30 = Column(Float)
    poverty_rate_ref_30_39 = Column(Float)
    poverty_rate_ref_40_49 = Column(Float)
    poverty_rate_ref_50_59 = Column(Float)
    poverty_rate_ref_60_74 = Column(Float)
    poverty_rate_ref_ge75 = Column(Float)
    poverty_rate_owners = Column(Float)
    poverty_rate_tenants = Column(Float)
    share_activity_income = Column(Float)
    share_salaries = Column(Float)
    share_unemployment_benefits = Column(Float)
    share_self_employment = Column(Float)
    share_pensions = Column(Float)
    share_property_income = Column(Float)
    share_social_benefits = Column(Float)
    share_family_benefits = Column(Float)
    share_minimum_income = Column(Float)
    share_housing_benefits = Column(Float)
    share_taxes = Column(Float)
    d1 = Column(Float)
    d9 = Column(Float)
    interdecile_ratio = Column(Float)
    d2 = Column(Float)
    d3 = Column(Float)
    d4 = Column(Float)
    d6 = Column(Float)
    d7 = Column(Float)
    d8 = Column(Float)
    q1 = Column(Float)
    q3 = Column(Float)
    gini = Column(Float)
    s80s20 = Column(Float)
    interquartile_range = Column(Float)
    poverty_rate_ind_lt18 = Column(Float)
    poverty_rate_ind_18_29 = Column(Float)
    poverty_rate_ind_30_39 = Column(Float)
    poverty_rate_ind_40_49 = Column(Float)
    poverty_rate_ind_50_64 = Column(Float)
    poverty_rate_ind_65_74 = Column(Float)
    poverty_rate_ind_ge75 = Column(Float)
    median_ind_lt18 = Column(Float)
    median_ind_18_29 = Column(Float)
    median_ind_30_39 = Column(Float)
    median_ind_40_49 = Column(Float)
    median_ind_50_64 = Column(Float)
    median_ind_65_74 = Column(Float)
    median_ind_ge75 = Column(Float)


# --------------------------------------------------------------------------- Éducation nationale
_SCHOOL_FLOATS = ['ips', 'ips_sd', 'ips_gt', 'ips_pro', 'ips_post_bac', 'ips_percentile', 'ips_national',
                  'ips_national_public', 'ips_national_private', 'ips_academic', 'ips_departmental',
                  'ips_departmental_public', 'ips_departmental_private', 'remoteness', 'remoteness_percentile',
                  'dnb_candidates', 'dnb_success_rate', 'dnb_success_va', 'dnb_written_score', 'dnb_written_va',
                  'dnb_mentions_rate', 'dnb_tb_rate', 'access_6_3_rate', 'dnb_success_va_percentile',
                  'dnb_written_va_percentile',
                  'gt_candidates', 'gt_success_rate', 'gt_success_va', 'gt_access_rate', 'gt_access_va',
                  'gt_mentions_rate', 'gt_mentions_va', 'gt_success_va_percentile', 'gt_access_va_percentile',
                  'pro_candidates', 'pro_success_rate', 'pro_success_va', 'pro_access_rate', 'pro_access_va',
                  'pro_mentions_rate', 'pro_mentions_va', 'pro_success_va_percentile', 'pro_access_va_percentile']


class SchoolByYear(Base):
    """Indicateurs d'un établissement scolaire (IPS, valeurs ajoutées, éloignement) — migration b7d9f1a3c5e6."""
    __tablename__ = "schools_by_year"

    uai = Column(String(10), primary_key=True)
    year = Column(Integer, primary_key=True)        # rentrée (IPS, éloignement) ou session (examens)
    school_type = Column(String(10))                # ecole, college, lycee
    lycee_type = Column(String(10))                 # LEGT, LPO, LP
    name = Column(String)
    sector = Column(String(10))                     # public, private
    commune_code = Column(String(5), index=True)
    commune_name = Column(String)
    department_code = Column(String(3))
    ips_decile = Column(Integer)
    remoteness_decile = Column(Integer)


for _c in _SCHOOL_FLOATS:
    setattr(SchoolByYear, _c, Column(_c, Float))


class SchoolNationalByYear(Base):
    """Distribution nationale d'un indicateur par type d'établissement et année (moyenne, déciles)."""
    __tablename__ = "schools_national_by_year"

    school_type = Column(String(20), primary_key=True)  # ecole, college, lycee, lycee_LEGT, lycee_LPO, lycee_LP
    year = Column(Integer, primary_key=True)
    metric = Column(String(40), primary_key=True)
    establishments = Column(Integer)
    mean = Column(Float)
    d1 = Column(Float)
    d2 = Column(Float)
    d3 = Column(Float)
    d4 = Column(Float)
    d5 = Column(Float)
    d6 = Column(Float)
    d7 = Column(Float)
    d8 = Column(Float)
    d9 = Column(Float)


class SixthGradeAgeByTerritory(Base):
    """Âge des élèves à l'entrée en 6e (DEP, REG, FRANCE 'FM') — migration b7d9f1a3c5e6."""
    __tablename__ = "sixth_grade_age_by_territory"

    geo_level = Column(String(10), primary_key=True)
    geo_code = Column(String(10), primary_key=True)
    year = Column(Integer, primary_key=True)


for _g in ("total", "girls", "boys", "public", "private"):
    for _m in ("pupils", "on_time", "early", "late"):
        setattr(SixthGradeAgeByTerritory, f"{_m}_{_g}", Column(f"{_m}_{_g}", Float))


class ImmigrationByTerritory(Base):
    """Immigrés et étrangers (INSEE, recensement 2023) — voir migration c8e0a2b4d6f7."""
    __tablename__ = "immigration_by_territory"

    geo_level = Column(String(10), primary_key=True)   # COM, ARM, EPCI, DEP, REG, FRANCE
    geo_code = Column(String(10), primary_key=True)    # FRANCE : 'FM' (métropole)
    year = Column(Integer, primary_key=True)           # 2023


for _m in ['imm', 'imm_women', 'imm_lt15', 'imm_15_24', 'imm_25_54', 'imm_ge55', 'imm_employed_15p', 'imm_unemployed_15p', 'imm_retired_15p', 'imm_students_15p', 'imm_homemakers_15p', 'imm_other_inactive_15p', 'imm_employed_25_54', 'imm_women_25_54', 'imm_women_employed_25_54', 'imm_women_homemakers_25_54', 'imm_pcs1', 'imm_pcs2', 'imm_pcs3', 'imm_pcs4', 'imm_pcs5', 'imm_pcs6', 'nonimm', 'nonimm_women', 'nonimm_lt15', 'nonimm_15_24', 'nonimm_25_54', 'nonimm_ge55', 'nonimm_employed_15p', 'nonimm_unemployed_15p', 'nonimm_retired_15p', 'nonimm_students_15p', 'nonimm_homemakers_15p', 'nonimm_other_inactive_15p', 'nonimm_employed_25_54', 'nonimm_women_25_54', 'nonimm_women_employed_25_54', 'nonimm_women_homemakers_25_54', 'nonimm_pcs1', 'nonimm_pcs2', 'nonimm_pcs3', 'nonimm_pcs4', 'nonimm_pcs5', 'nonimm_pcs6', 'population', 'foreign', 'foreign_women', 'foreign_lt15', 'foreign_employed_15p', 'foreign_unemployed_15p', 'french', 'french_women', 'french_lt15', 'french_employed_15p', 'french_unemployed_15p']:
    setattr(ImmigrationByTerritory, _m, Column(_m, Float))
