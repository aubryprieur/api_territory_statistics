import os
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status, APIRouter
from fastapi.staticfiles import StaticFiles
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .services.population_service import PopulationService
from .services.historical_service import HistoricalService
from .services.birth_service import BirthService
from .services.geocode_service import GeoCodeService
from .services.revenue_service import RevenueService
from .services.family_service import FamilyService
from .services.childcare_service import ChildcareService
from .services.public_safety_service import PublicSafetyService
from .services.employment_service import EmploymentService
from .services.schooling_service import SchoolingService
from .services.family_employment_service import FamilyEmploymentService

from app.models import Birth  # Uniquement le modèle SQLAlchemy

from app.schemas import BirthSchema, FamilySchema
from app.schemas import (
    Population, HistoricalData, PopulationChildrenRate, PopulationChildrenEPCI,
    PopulationChildrenDepartment, PopulationChildrenRegion, PopulationChildrenFrance,
    Revenue, Childcare, PublicSafetyResponse,
    EmploymentResponse, SchoolingResponse, SchoolingData,
    FamilyEmploymentResponse, FamilyEmploymentDistribution
)

from app.database import get_db
from app.security import (
    Token, User, authenticate_user, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Importer les modules de rate limiting
import redis
from slowapi.storage import RedisStorage

# Connexion Redis (en production uniquement)
if not DEBUG:
    redis_client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=int(os.environ.get("REDIS_DB", "0")),
        password=os.environ.get("REDIS_PASSWORD", None)
    )
    limiter = Limiter(key_func=get_remote_address, storage_uri=redis_client)
else:
    # En développement, utilisez le stockage en mémoire par défaut
    limiter = Limiter(key_func=get_remote_address)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Charger les variables d'environnement en premier
load_dotenv(verbose=True)

# Créer l'application SANS dépendance globale
app = FastAPI(title="API Population")

# Ajouter le gestionnaire d'erreur pour le rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurer CORS
# Déterminer l'environnement
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Configuration CORS basée sur l'environnement
if DEBUG:
    # En mode développement, autoriser tous les domaines
    origins = ["*"]
else:
    # En production, autoriser uniquement des domaines spécifiques
    origins_str = os.environ.get("CORS_ORIGINS", "https://votre-domaine.com")
    origins = [origin.strip() for origin in origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"] if not DEBUG else ["*"],
    allow_headers=["Authorization", "Content-Type"] if not DEBUG else ["*"],
)

# Récupérer les limites depuis les variables d'environnement
DEFAULT_RATE = os.environ.get("RATE_LIMIT_DEFAULT", "60/minute")
AUTH_RATE = os.environ.get("RATE_LIMIT_AUTH", "5/minute")
HIGH_LOAD_RATE = os.environ.get("RATE_LIMIT_HIGH_LOAD", "20/minute")


# L'endpoint /token directement sur l'app (non protégé)
@app.post("/token", response_model=Token)
@limiter.limit(AUTH_RATE)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Monter les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialiser les services
population_service = PopulationService()
historical_service = HistoricalService()
birth_service = BirthService()
geocode_service = GeoCodeService()
revenue_service = RevenueService()
family_service = FamilyService()
childcare_service = ChildcareService()
public_safety_service = PublicSafetyService()
employment_service = EmploymentService()
schooling_service = SchoolingService()
family_employment_service = FamilyEmploymentService()

# Créer un router protégé pour tous les autres endpoints
protected_router = APIRouter(dependencies=[Depends(get_current_user)])

# Tous les endpoints existants, mais maintenant sur le router protégé
@protected_router.get("/", dependencies=[Depends(limiter.limit(DEFAULT_RATE))])
async def root():
    return {"message": "API Population 2021"}

@protected_router.get("/population/{code}",
    response_model=List[Population],
    dependencies=[Depends(limiter.limit(HIGH_LOAD_RATE))],
    summary="Obtenir la structure de la population d'une commune",
    description="Récupère la répartition détaillée de la population d'une commune par sexe et par âge (de 0 à 100 ans)",
    response_description="Liste détaillée des effectifs de population par sexe et âge")
async def get_population_by_code(code: str):
    """
    Récupère la pyramide des âges d'une commune :

    - **code**: Code INSEE de la commune

    Retourne une liste où chaque élément contient :
    - Le niveau géographique (NIVGEO)
    - Le code de la commune (CODGEO)
    - Le nom de la commune (LIBGEO)
    - Le sexe (SEXE) : 1 pour les hommes, 2 pour les femmes
    - L'âge (AGED100) : de 0 à 100 ans
    - Le nombre de personnes (NB)
    """
    data = population_service.get_by_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Code non trouvé")
    return data

@protected_router.get("/population/children/commune/{code}",
    response_model=PopulationChildrenRate,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les données des enfants de 0-5 ans pour une commune",
    description="Récupère les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour une commune",
    response_description="Les données démographiques incluant la population totale, le nombre d'enfants par tranche d'âge et leurs taux")
async def get_commune_children(code: str):
    """
    Obtient les statistiques des enfants pour une commune :

    - **code**: Code INSEE de la commune
    """
    return population_service.get_population_and_children_rate(code)

@protected_router.get("/population/children/epci/{epci}",
    response_model=PopulationChildrenEPCI,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les données des enfants de 0-5 ans pour un EPCI",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un EPCI",
    response_description="Les données démographiques incluant la population totale de l'EPCI, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
async def get_epci_children(epci: str):
    """
    Agrège les statistiques des enfants pour un EPCI :

    - **epci**: Code de l'EPCI
    """
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@protected_router.get("/population/children/department/{dep}",
    response_model=PopulationChildrenDepartment,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les données des enfants de 0-5 ans pour un département",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un département",
    response_description="Les données démographiques incluant la population totale du département, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
async def get_department_children(dep: str):
    """
    Agrège les statistiques des enfants pour un département :

    - **dep**: Code du département
    """
    return population_service.aggregate_children_by_department(dep, geocode_service)

@protected_router.get("/population/children/region/{reg}",
    response_model=PopulationChildrenRegion,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les données des enfants de 0-5 ans pour une région",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'une région",
    response_description="Les données démographiques incluant la population totale de la région, le nombre d'enfants par tranche d'âge, leurs taux, le nombre de communes et de départements")
async def get_region_children(reg: str):
    """
    Agrège les statistiques des enfants pour une région :

    - **reg**: Code de la région
    """
    return population_service.aggregate_children_by_region(reg, geocode_service)

@protected_router.get("/population/children/france",
    response_model=PopulationChildrenFrance,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les données des enfants de 0-5 ans pour la France entière",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour l'ensemble de la France",
    response_description="Les données démographiques incluant la population totale nationale, le nombre d'enfants par tranche d'âge, leurs taux, le nombre de communes, de départements et de régions")
async def get_france_children():
    """
    Agrège les statistiques des enfants au niveau national
    """
    return population_service.aggregate_children_france(geocode_service)

@protected_router.get("/historical/{code}",
    response_model=List[HistoricalData],
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir l'historique de population d'une commune depuis 1968",
    description="""Récupère les données historiques de population d'une commune pour les recensements de :
- 1968 (D68_POP)
- 1975 (D75_POP)
- 1982 (D82_POP)
- 1990 (D90_POP)
- 1999 (D99_POP)
- 2010 (P10_POP)
- 2015 (P15_POP)
- 2021 (P21_POP)

Cette évolution permet d'observer les tendances démographiques sur plus de 50 ans.""",
    response_description="Les données de population pour chaque recensement depuis 1968")
async def get_historical_by_code(code: str):
    """
    Obtient l'évolution historique de la population d'une commune :

    - **code**: Code INSEE de la commune

    Retourne pour chaque recensement :
    - CODGEO : Code INSEE de la commune
    - P21_POP : Population en 2021
    - P15_POP : Population en 2015
    - P10_POP : Population en 2010
    - D99_POP : Population en 1999
    - D90_POP : Population en 1990
    - D82_POP : Population en 1982
    - D75_POP : Population en 1975
    - D68_POP : Population en 1968
    """
    return historical_service.get_by_code(code)


@protected_router.get("/geocodes/{code}")
async def get_geocode(code: str):
   return geocode_service.get_by_code(code)

@protected_router.get("/geocodes/region/{reg}")
async def get_by_region(reg: str):
   return geocode_service.get_by_region(reg)

@protected_router.get("/geocodes/department/{dep}")
async def get_by_department(dep: str):
   return geocode_service.get_by_department(dep)

@protected_router.get("/births/{code}",
    response_model=List[BirthSchema],
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les naissances par commune",
    description="Récupère les données historiques des naissances pour une commune spécifique",
    response_description="Les données de naissance annuelles pour la commune")
async def get_births_by_code(code: str):
    """
    Récupère les données de naissance pour une commune :

    - **code**: Code INSEE de la commune
    """
    return birth_service.get_by_code(code)

@protected_router.get("/geocodes/epci/{epci}/births",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les naissances agrégées par EPCI",
    description="Récupère et agrège les données de naissance pour toutes les communes d'un EPCI",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes et l'évolution par année")
async def get_epci_births(epci: str):
    """
    Agrège les naissances au niveau EPCI :

    - **epci**: Code de l'EPCI
    """
    return geocode_service.aggregate_births_by_epci(epci, birth_service)

@protected_router.get("/geocodes/department/{dep}/births",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les naissances agrégées par département",
    description="Récupère et agrège les données de naissance pour toutes les communes d'un département",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes et l'évolution par année")
async def get_department_births(dep: str):
    """
    Agrège les naissances au niveau départemental :

    - **dep**: Code du département
    """
    return geocode_service.aggregate_births_by_department(dep, birth_service)

@protected_router.get("/geocodes/region/{reg}/births",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les naissances agrégées par région",
    description="Récupère et agrège les données de naissance pour toutes les communes d'une région",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes, le nombre de départements et l'évolution par année")
async def get_region_births(reg: str):
    """
    Agrège les naissances au niveau régional :

    - **reg**: Code de la région
    """
    return geocode_service.aggregate_births_by_region(reg, birth_service)

@protected_router.get("/geocodes/france/births",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les naissances agrégées pour la France entière",
    description="Récupère et agrège les données de naissance pour toutes les communes de France",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes, le nombre de départements, le nombre de régions et l'évolution par année")
async def get_france_births():
    """
    Agrège les naissances au niveau national
    """
    return geocode_service.aggregate_births_france(birth_service)

@protected_router.get("/revenues/median/commune/{code}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les revenus médians d'une commune",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'une commune depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour la commune")
async def get_commune_median_revenues(code: str):
    """
    Obtient les données de revenus pour une commune :

    - **code**: Code INSEE de la commune

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues(code)

@protected_router.get("/revenues/median/epci/{code}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les revenus médians d'un EPCI",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'un EPCI depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour l'EPCI")
async def get_epci_median_revenues(code: str):
    """
    Obtient les données de revenus agrégées pour un EPCI :

    - **code**: Code de l'EPCI

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages de l'EPCI
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_epci(code)

@protected_router.get("/revenues/median/department/{code}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les revenus médians d'un département",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'un département depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour le département")
async def get_department_median_revenues(code: str):
    """
    Obtient les données de revenus agrégées pour un département :

    - **code**: Code du département

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages du département
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_department(code)

@protected_router.get("/revenues/median/region/{code}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les revenus médians d'une région",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'une région depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour la région")
async def get_region_median_revenues(code: str):
    """
    Obtient les données de revenus agrégées pour une région :

    - **code**: Code de la région

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages de la région
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_region(code)

@protected_router.get("/revenues/median/france",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les revenus médians de la France",
    description="Récupère l'historique des revenus médians et des taux de pauvreté au niveau national depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour la France entière")
async def get_france_median_revenues():
    """
    Obtient les données de revenus agrégées au niveau national

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages en France
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_france()

@protected_router.get("/childcare/commune/{code}",
    response_model=dict,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux de couverture des modes d'accueil pour une commune",
    description="""Récupère les taux de couverture des différents modes d'accueil pour une commune depuis 2017.

Les modes d'accueil incluent :
- Accueil collectif PSU (crèches PSU)
- Accueil collectif hors PSU
- Total accueil collectif (EAJE)
- Préscolarisation
- Assistantes maternelles
- Garde à domicile
- Total accueil individuel
- Couverture globale (tous modes d'accueil)""",
    response_description="Les taux de couverture par année et par mode d'accueil")
async def get_commune_childcare(
    code: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les taux de couverture pour une commune :

    - **code**: Code INSEE de la commune
    - **start_year**: Année de début (optionnel, >= 2017)
    - **end_year**: Année de fin (optionnel, <= 2022)
    """
    return childcare_service.get_coverage_by_commune(code, start_year, end_year)

@protected_router.get("/childcare/epci/{epci}",
    response_model=dict,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux de couverture des modes d'accueil pour un EPCI",
    description="""Récupère les taux de couverture des différents modes d'accueil pour un EPCI (Établissement Public de Coopération Intercommunale) depuis 2017.

Les modes d'accueil incluent :
- Accueil collectif PSU (crèches PSU)
- Accueil collectif hors PSU
- Total accueil collectif (EAJE)
- Préscolarisation
- Assistantes maternelles
- Garde à domicile
- Total accueil individuel
- Couverture globale (tous modes d'accueil)

Inclut également les informations sur le département de rattachement.""",
    response_description="Les taux de couverture par année et par mode d'accueil, avec les informations territoriales")
async def get_epci_childcare(
    epci: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les taux de couverture pour un EPCI :

    - **epci**: Code de l'EPCI
    - **start_year**: Année de début (optionnel, >= 2017)
    - **end_year**: Année de fin (optionnel, <= 2022)
    """
    return childcare_service.get_coverage_by_epci(epci, start_year, end_year)

@protected_router.get("/childcare/department/{dep}",
    response_model=dict,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux de couverture des modes d'accueil pour un département",
    description="""Récupère les taux de couverture des différents modes d'accueil pour un département depuis 2017.

Les modes d'accueil incluent :
- Accueil collectif PSU (crèches PSU)
- Accueil collectif hors PSU
- Total accueil collectif (EAJE)
- Préscolarisation
- Assistantes maternelles
- Garde à domicile
- Total accueil individuel
- Couverture globale (tous modes d'accueil)

Inclut également les informations sur la région de rattachement.""",
    response_description="Les taux de couverture par année et par mode d'accueil, avec les informations territoriales")
async def get_department_childcare(
    dep: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les taux de couverture pour un département :

    - **dep**: Code du département
    - **start_year**: Année de début (optionnel, >= 2017)
    - **end_year**: Année de fin (optionnel, <= 2022)
    """
    return childcare_service.get_coverage_by_department(dep, start_year, end_year)

@protected_router.get("/childcare/region/{reg}",
    response_model=dict,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux de couverture des modes d'accueil pour une région",
    description="""Récupère les taux de couverture des différents modes d'accueil pour une région depuis 2017.

Les modes d'accueil incluent :
- Accueil collectif PSU (crèches PSU)
- Accueil collectif hors PSU
- Total accueil collectif (EAJE)
- Préscolarisation
- Assistantes maternelles
- Garde à domicile
- Total accueil individuel
- Couverture globale (tous modes d'accueil)""",
    response_description="Les taux de couverture par année et par mode d'accueil")
async def get_region_childcare(
    reg: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les taux de couverture pour une région :

    - **reg**: Code de la région
    - **start_year**: Année de début (optionnel, >= 2017)
    - **end_year**: Année de fin (optionnel, <= 2022)
    """
    return childcare_service.get_coverage_by_region(reg, start_year, end_year)

@protected_router.get("/childcare/france",
    response_model=dict,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux de couverture des modes d'accueil pour la France",
    description="""Récupère les taux de couverture des différents modes d'accueil au niveau national depuis 2017.

Les modes d'accueil incluent :
- Accueil collectif PSU (crèches PSU)
- Accueil collectif hors PSU
- Total accueil collectif (EAJE)
- Préscolarisation
- Assistantes maternelles
- Garde à domicile
- Total accueil individuel
- Couverture globale (tous modes d'accueil)""",
    response_description="Les taux de couverture par année et par mode d'accueil pour la France entière")
async def get_france_childcare(
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les taux de couverture pour la France entière :

    - **start_year**: Année de début (optionnel, >= 2017)
    - **end_year**: Année de fin (optionnel, <= 2022)
    """
    return childcare_service.get_coverage_france(start_year, end_year)

@protected_router.get("/families/commune/{code}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les statistiques des familles pour une commune",
    description="""Récupère l'évolution de la composition des familles pour une commune depuis 2010.

Les données incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
async def get_commune_families(
    code: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles pour une commune :

    - **code**: Code INSEE de la commune
    - **start_year**: Année de début (optionnel, >= 2010)
    - **end_year**: Année de fin (optionnel, <= 2021)
    """
    return family_service.get_families_by_commune(code, start_year, end_year)

@protected_router.get("/families/epci/{epci}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les statistiques des familles pour un EPCI",
    description="""Récupère l'évolution de la composition des familles pour un EPCI depuis 2010.

Les données sont agrégées pour toutes les communes de l'EPCI et incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
async def get_epci_families(
    epci: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour un EPCI :

    - **epci**: Code de l'EPCI
    - **start_year**: Année de début (optionnel, >= 2010)
    - **end_year**: Année de fin (optionnel, <= 2021)
    """
    return family_service.get_families_by_epci(epci, start_year, end_year)

@protected_router.get("/families/department/{dep}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les statistiques des familles pour un département",
    description="""Récupère l'évolution de la composition des familles pour un département depuis 2010.

Les données sont agrégées pour toutes les communes du département et incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
async def get_department_families(
    dep: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour un département :

    - **dep**: Code du département
    - **start_year**: Année de début (optionnel, >= 2010)
    - **end_year**: Année de fin (optionnel, <= 2021)
    """
    return family_service.get_families_by_department(dep, start_year, end_year)

@protected_router.get("/families/region/{reg}",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les statistiques des familles pour une région",
    description="""Récupère l'évolution de la composition des familles pour une région depuis 2010.

Les données sont agrégées pour toutes les communes de la région et incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
async def get_region_families(
    reg: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour une région :

    - **reg**: Code de la région
    - **start_year**: Année de début (optionnel, >= 2010)
    - **end_year**: Année de fin (optionnel, <= 2021)
    """
    return family_service.get_families_by_region(reg, start_year, end_year)

@protected_router.get("/families/france",
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les statistiques des familles pour la France entière",
    description="""Récupère l'évolution de la composition des familles au niveau national depuis 2010.

Les données incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées, permettant d'observer
les tendances démographiques nationales sur la structure des familles.""",
    response_description="Statistiques nationales annuelles avec analyse de l'évolution")
async def get_france_families(
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées au niveau national :

    - **start_year**: Année de début (optionnel, >= 2010)
    - **end_year**: Année de fin (optionnel, <= 2021)
    """
    return family_service.get_families_france(start_year, end_year)

@protected_router.get("/public-safety/commune/{code}",
   response_model=PublicSafetyResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir les indicateurs de sécurité d'une commune",
   description="""Récupère les indicateurs de sécurité publique pour une commune et ses territoires parents (département et région).

Les données incluent pour chaque année :
- Les taux d'atteintes aux personnes
- Les taux d'atteintes aux biens
- Les taux de violences intrafamiliales
- Les taux d'infractions économiques et financières

Les données communales sont comparées avec celles du département et de la région pour permettre une mise en perspective territoriale.""",
   response_description="Indicateurs de sécurité communaux, départementaux et régionaux")
async def get_commune_public_safety(code: str):
   """
   Obtient les indicateurs de sécurité pour une commune :

   - **code**: Code INSEE de la commune

   La réponse inclut :
   - Les données de la commune
   - Les données du département parent
   - Les données de la région parente
   """
   return public_safety_service.get_by_commune(code)

@protected_router.get("/public-safety/department/{dep}",
    response_model=PublicSafetyResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les indicateurs de sécurité d'un département",
    description="""Récupère les indicateurs de sécurité publique pour un département et sa région parente.

Les données incluent pour chaque année :
- Les taux d'atteintes aux personnes
- Les taux d'atteintes aux biens
- Les taux de violences intrafamiliales
- Les taux d'infractions économiques et financières

Les données départementales sont comparées avec celles de la région parente.""",
    response_description="Indicateurs de sécurité départementaux et régionaux")
async def get_department_public_safety(dep: str):
    """
    Obtient les indicateurs de sécurité pour un département :

    - **dep**: Code du département
    """
    return public_safety_service.get_by_department(dep)

@protected_router.get("/public-safety/region/{reg}",
    response_model=PublicSafetyResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les indicateurs de sécurité d'une région",
    description="""Récupère les indicateurs de sécurité publique pour une région.

Les données incluent pour chaque année :
- Les taux d'atteintes aux personnes
- Les taux d'atteintes aux biens
- Les taux de violences intrafamiliales
- Les taux d'infractions économiques et financières""",
    response_description="Indicateurs de sécurité régionaux")
async def get_region_public_safety(reg: str):
    """
    Obtient les indicateurs de sécurité pour une région :

    - **reg**: Code de la région
    """
    return public_safety_service.get_by_region(reg)

@protected_router.get("/employment/rates/commune/{code}",
    response_model=EmploymentResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux d'emploi des femmes pour une commune",
    description="""Récupère les indicateurs d'emploi des femmes pour une commune en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes de la commune")
async def get_commune_employment_rates(code: str):
    """
    Obtient les statistiques d'emploi des femmes pour une commune :

    - **code**: Code INSEE de la commune
    """
    return employment_service.get_commune_rates(code)

@protected_router.get("/employment/rates/epci/{epci}",
    response_model=EmploymentResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux d'emploi des femmes pour un EPCI",
    description="""Récupère les indicateurs d'emploi des femmes agrégés pour un EPCI (Établissement Public de Coopération Intercommunale) en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes agrégés pour l'EPCI")
async def get_epci_employment_rates(epci: str):
    """
    Obtient les statistiques d'emploi des femmes agrégées pour un EPCI :

    - **epci**: Code de l'EPCI
    """
    return employment_service.get_epci_rates(epci)

@protected_router.get("/employment/rates/department/{dep}",
    response_model=EmploymentResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux d'emploi des femmes pour un département",
    description="""Récupère les indicateurs d'emploi des femmes agrégés pour un département en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes agrégés pour le département")
async def get_department_employment_rates(dep: str):
    """
    Obtient les statistiques d'emploi des femmes agrégées pour un département :

    - **dep**: Code du département
    """
    return employment_service.get_department_rates(dep)

@protected_router.get("/employment/rates/region/{reg}",
    response_model=EmploymentResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux d'emploi des femmes pour une région",
    description="""Récupère les indicateurs d'emploi des femmes agrégés pour une région en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes agrégés pour la région")
async def get_region_employment_rates(reg: str):
    """
    Obtient les statistiques d'emploi des femmes agrégées pour une région :

    - **reg**: Code de la région
    """
    return employment_service.get_region_rates(reg)

@protected_router.get("/employment/rates/france",
    response_model=EmploymentResponse,
    dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
    summary="Obtenir les taux d'emploi des femmes pour la France",
    description="""Récupère les indicateurs d'emploi des femmes au niveau national en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes au niveau national")
async def get_france_employment_rates():
    """
    Obtient les statistiques d'emploi des femmes au niveau national
    """
    return employment_service.get_france_rates()

@protected_router.get("/education/schooling/commune/{code}",
   response_model=SchoolingResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir les taux de scolarisation pour une commune",
   description="""Récupère l'évolution des taux de scolarisation par tranche d'âge pour une commune sur la période 2017-2021.

Les données incluent pour chaque année :
- Pour les enfants de 2 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation
- Pour les enfants de 3 à 5 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation""",
   response_description="Statistiques annuelles de scolarisation pour la commune")
async def get_commune_schooling(code: str):
   """
   Obtient les taux de scolarisation pour une commune :

   - **code**: Code INSEE de la commune
   """
   return schooling_service.get_commune_schooling(code)

@protected_router.get("/education/schooling/epci/{epci}",
   response_model=SchoolingResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir les taux de scolarisation pour un EPCI",
   description="""Récupère l'évolution des taux de scolarisation par tranche d'âge agrégés pour un EPCI (Établissement Public de Coopération Intercommunale) sur la période 2017-2021.

Les données incluent pour chaque année :
- Pour les enfants de 2 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation
- Pour les enfants de 3 à 5 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation""",
   response_description="Statistiques annuelles de scolarisation agrégées pour l'EPCI")
async def get_epci_schooling(epci: str):
   """
   Obtient les taux de scolarisation agrégés pour un EPCI :

   - **epci**: Code de l'EPCI
   """
   return schooling_service.get_epci_schooling(epci)

@protected_router.get("/education/schooling/department/{dep}",
   response_model=SchoolingResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir les taux de scolarisation pour un département",
   description="""Récupère l'évolution des taux de scolarisation par tranche d'âge agrégés pour un département sur la période 2017-2021.

Les données incluent pour chaque année :
- Pour les enfants de 2 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation
- Pour les enfants de 3 à 5 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation""",
   response_description="Statistiques annuelles de scolarisation agrégées pour le département")
async def get_department_schooling(dep: str):
   """
   Obtient les taux de scolarisation agrégés pour un département :

   - **dep**: Code du département
   """
   return schooling_service.get_department_schooling(dep)

@protected_router.get("/education/schooling/region/{reg}",
   response_model=SchoolingResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir les taux de scolarisation pour une région",
   description="""Récupère l'évolution des taux de scolarisation par tranche d'âge agrégés pour une région sur la période 2017-2021.

Les données incluent pour chaque année :
- Pour les enfants de 2 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation
- Pour les enfants de 3 à 5 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation""",
   response_description="Statistiques annuelles de scolarisation agrégées pour la région")
async def get_region_schooling(reg: str):
   """
   Obtient les taux de scolarisation agrégés pour une région :

   - **reg**: Code de la région
   """
   return schooling_service.get_region_schooling(reg)

@protected_router.get("/education/schooling/france",
   response_model=SchoolingResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir les taux de scolarisation pour la France",
   description="""Récupère l'évolution des taux de scolarisation par tranche d'âge au niveau national sur la période 2017-2021.

Les données incluent pour chaque année :
- Pour les enfants de 2 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation
- Pour les enfants de 3 à 5 ans :
 * Nombre total d'enfants
 * Nombre d'enfants scolarisés
 * Taux de scolarisation""",
   response_description="Statistiques annuelles de scolarisation au niveau national")
async def get_france_schooling():
   """
   Obtient les taux de scolarisation au niveau national
   """
   return schooling_service.get_france_schooling()

# Routes pour les 0-2 ans
@protected_router.get("/families/employment/under3/commune/{code}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de moins de 3 ans pour une commune",
   description="""Récupère la distribution des situations d'emploi des familles ayant des enfants de moins de 3 ans pour une commune en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi""",
   response_description="Distribution des situations d'emploi des familles avec leur pourcentage")
async def get_commune_family_employment_under3(code: str):
   """
   Obtient la répartition des situations d'emploi pour une commune :

   - **code**: Code INSEE de la commune
   """
   return family_employment_service.get_commune_distribution(code, age_group="0")

@protected_router.get("/families/employment/under3/epci/{epci}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de moins de 3 ans pour un EPCI",
   description="""Récupère la distribution agrégée des situations d'emploi des familles ayant des enfants de moins de 3 ans pour un EPCI (Établissement Public de Coopération Intercommunale) en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi""",
   response_description="Distribution agrégée des situations d'emploi des familles avec leur pourcentage")
async def get_epci_family_employment_under3(epci: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un EPCI :

   - **epci**: Code de l'EPCI
   """
   return family_employment_service.get_epci_distribution(epci, age_group="0")

@protected_router.get("/families/employment/under3/department/{dep}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de moins de 3 ans pour un département",
   description="""Récupère la distribution agrégée des situations d'emploi des familles ayant des enfants de moins de 3 ans pour un département en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi""",
   response_description="Distribution agrégée des situations d'emploi des familles avec leur pourcentage")
async def get_department_family_employment_under3(dep: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un département :

   - **dep**: Code du département
   """
   return family_employment_service.get_department_distribution(dep, age_group="0")

@protected_router.get("/families/employment/under3/region/{reg}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de moins de 3 ans pour une région",
   description="""Récupère la distribution agrégée des situations d'emploi des familles ayant des enfants de moins de 3 ans pour une région en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi""",
   response_description="Distribution agrégée des situations d'emploi des familles avec leur pourcentage")
async def get_region_family_employment_under3(reg: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour une région :

   - **reg**: Code de la région
   """
   return family_employment_service.get_region_distribution(reg, age_group="0")

@protected_router.get("/families/employment/under3/france",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de moins de 3 ans pour la France",
   description="""Récupère la distribution nationale des situations d'emploi des familles ayant des enfants de moins de 3 ans en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi""",
   response_description="Distribution nationale des situations d'emploi des familles avec leur pourcentage")
async def get_france_family_employment_under3():
   """
   Obtient la répartition des situations d'emploi au niveau national
   """
   return family_employment_service.get_france_distribution(age_group="0")

# Routes pour les 3-5 ans
@protected_router.get("/families/employment/3to5/commune/{code}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de 3 à 5 ans pour une commune",
   description="""Récupère la distribution des situations d'emploi des familles ayant des enfants de 3 à 5 ans pour une commune en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi

Pour chaque situation, les données indiquent :
- Le nombre de familles concernées
- Le pourcentage par rapport au total des familles de la commune""",
   response_description="Distribution des situations d'emploi des familles avec leur nombre et pourcentage")
async def get_commune_family_employment_3to5(code: str):
   """
   Obtient la répartition des situations d'emploi pour une commune :

   - **code**: Code INSEE de la commune
   """
   return family_employment_service.get_commune_distribution(code, age_group="3")

@protected_router.get("/families/employment/3to5/epci/{epci}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de 3 à 5 ans pour un EPCI",
   description="""Récupère la distribution agrégée des situations d'emploi des familles ayant des enfants de 3 à 5 ans pour un EPCI (Établissement Public de Coopération Intercommunale) en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi

Pour chaque situation, les données agrégées indiquent :
- Le nombre total de familles concernées dans l'EPCI
- Le pourcentage par rapport au total des familles de l'EPCI""",
   response_description="Distribution agrégée des situations d'emploi des familles avec leur nombre et pourcentage")
async def get_epci_family_employment_3to5(epci: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un EPCI :

   - **epci**: Code de l'EPCI
   """
   return family_employment_service.get_epci_distribution(epci, age_group="3")

@protected_router.get("/families/employment/3to5/department/{dep}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de 3 à 5 ans pour un département",
   description="""Récupère la distribution agrégée des situations d'emploi des familles ayant des enfants de 3 à 5 ans pour un département en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi

Pour chaque situation, les données agrégées indiquent :
- Le nombre total de familles concernées dans le département
- Le pourcentage par rapport au total des familles du département""",
   response_description="Distribution agrégée des situations d'emploi des familles avec leur nombre et pourcentage")
async def get_department_family_employment_3to5(dep: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un département :

   - **dep**: Code du département
   """
   return family_employment_service.get_department_distribution(dep, age_group="3")

@protected_router.get("/families/employment/3to5/region/{reg}",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de 3 à 5 ans pour une région",
   description="""Récupère la distribution agrégée des situations d'emploi des familles ayant des enfants de 3 à 5 ans pour une région en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi

Pour chaque situation, les données agrégées indiquent :
- Le nombre total de familles concernées dans la région
- Le pourcentage par rapport au total des familles de la région""",
   response_description="Distribution agrégée des situations d'emploi des familles avec leur nombre et pourcentage")
async def get_region_family_employment_3to5(reg: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour une région :

   - **reg**: Code de la région
   """
   return family_employment_service.get_region_distribution(reg, age_group="3")

@protected_router.get("/families/employment/3to5/france",
   response_model=FamilyEmploymentResponse,
   dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
   summary="Obtenir la répartition des situations d'emploi des familles avec enfants de 3 à 5 ans pour la France",
   description="""Récupère la distribution nationale des situations d'emploi des familles ayant des enfants de 3 à 5 ans en 2021.

Les situations analysées sont :
- Familles monoparentales :
 * Homme actif ayant un emploi
 * Homme sans emploi
 * Femme active ayant un emploi
 * Femme sans emploi
- Couples avec enfant(s) :
 * Deux parents actifs ayant un emploi
 * Homme actif ayant un emploi, conjoint sans emploi
 * Femme active ayant un emploi, conjoint sans emploi
 * Aucun parent actif ayant un emploi

Pour chaque situation, les données indiquent :
- Le nombre total de familles concernées en France
- Le pourcentage par rapport au total des familles en France""",
   response_description="Distribution nationale des situations d'emploi des familles avec leur nombre et pourcentage")
async def get_france_family_employment_3to5():
   """
   Obtient la répartition des situations d'emploi au niveau national
   """
   return family_employment_service.get_france_distribution(age_group="3")

@protected_router.get("/families/{level}/{code}",
  dependencies=[Depends(limiter.limit(DEFAULT_RATE))],
  summary="Obtenir l'évolution de la composition des familles par niveau géographique",
  description="""Récupère l'évolution historique de la composition des familles depuis 2010 pour le niveau géographique choisi.

Les niveaux géographiques disponibles sont :
- commune : Données à l'échelle communale
- epci : Données agrégées à l'échelle de l'EPCI (Établissement Public de Coopération Intercommunale)
- department : Données agrégées à l'échelle départementale
- region : Données agrégées à l'échelle régionale

Pour chaque année, les données incluent :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant

L'évolution est calculée entre les années spécifiées (start_year et end_year) et indique pour chaque catégorie :
- La valeur de départ
- La valeur finale
- Le pourcentage d'évolution
- La période concernée""")
async def get_families(
   level: str,
   code: str,
   start_year: int = None,
   end_year: int = None
):
   """
   Obtient l'évolution de la composition des familles pour un territoire :

   - **level**: Niveau géographique ('commune', 'epci', 'department' ou 'region')
   - **code**: Code du territoire (INSEE, EPCI, département ou région)
   - **start_year**: Année de début pour le calcul de l'évolution (optionnel, >= 2010)
   - **end_year**: Année de fin pour le calcul de l'évolution (optionnel, <= 2021)
   """
   if level == "commune":
       return family_service.get_families_by_commune(code, start_year, end_year)
   elif level == "epci":
       return family_service.get_families_by_epci(code, geocode_service, start_year, end_year)
   elif level == "department":
       return family_service.get_families_by_department(code, geocode_service, start_year, end_year)
   elif level == "region":
       return family_service.get_families_by_region(code, geocode_service, start_year, end_year)
   else:
       raise HTTPException(status_code=404, detail=f"Level {level} not found")

# Inclure le router protégé dans l'app
app.include_router(protected_router)
