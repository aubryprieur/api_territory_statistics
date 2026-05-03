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
