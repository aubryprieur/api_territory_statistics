from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func, Index, UniqueConstraint
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
