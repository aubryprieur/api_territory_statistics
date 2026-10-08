# 1. Imports standards et bibliothèques tierces
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status, APIRouter, Request
from fastapi.staticfiles import StaticFiles
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

# 2. Imports pour le rate limiting (avant utilisation)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 3. Imports des modules internes
from .services.population_service import PopulationService
from .services.historical_service import HistoricalService
from .services.birth_service import BirthService
from .services.geocode_service import GeoCodeService
from .services.revenue_service import RevenueService
from .services.family_service import FamilyService
from .services.household_service import HouseholdService
from .services.education_training_service import EducationTrainingService
from .services.employment_activity_service import EmploymentActivityService
from .services.housing_service import HousingService
from .services.population_structure_service import PopulationStructureService
from .services.childcare_offer_service import ChildcareOfferService
from .services.caf_benefits_service import CafBenefitsService
from .services.revenues_service import RevenuesService
from .services.schools_service import SchoolsService, SixthGradeService
from .services.immigration_service import ImmigrationService
from .services.childcare_service import ChildcareService
from .services.public_safety_service import PublicSafetyService
from .services.employment_service import EmploymentService
from .services.schooling_service import SchoolingService
from .services.family_employment_service import FamilyEmploymentService

from .routers.iris import router as iris_router
from .routers.iris_families import router as iris_families_router
from .routers.iris_housing import router as iris_housing_router
from .routers.iris_education import router as iris_education_router
from .routers.iris_activity import router as iris_activity_router

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

# 4. Charger les variables d'environnement en premier
load_dotenv(verbose=True)

# 5. Déterminer l'environnement
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# 6. Configuration des limites de taux
DEFAULT_RATE = os.environ.get("RATE_LIMIT_DEFAULT", "60/minute")
AUTH_RATE = os.environ.get("RATE_LIMIT_AUTH", "5/minute")
HIGH_LOAD_RATE = os.environ.get("RATE_LIMIT_HIGH_LOAD", "20/minute")

# 7. Rate limiter (stockage en mémoire, par worker)
limiter = Limiter(key_func=get_remote_address)

# 8. Créer l'application SANS dépendance globale
app = FastAPI(title="API Population")

# Ajouter les routeurs à l'application
from app.api import api_router
app.include_router(api_router)
app.include_router(iris_router)
app.include_router(iris_families_router)
app.include_router(iris_housing_router)
app.include_router(iris_education_router)
app.include_router(iris_activity_router)

# 9. Ajouter le gestionnaire d'erreur pour le rate limiting
app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # Commentez ou supprimez cette ligne

# Définissez votre fonction gestionnaire personnalisée
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded"},
    )

# Enregistrez correctement le gestionnaire
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# 10. Configurer CORS
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

# Compression gzip des réponses > 1 Ko (si le client envoie Accept-Encoding: gzip)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 11. Monter les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# 12. Initialiser les services
population_service = PopulationService()
historical_service = HistoricalService()
birth_service = BirthService()
geocode_service = GeoCodeService()
revenue_service = RevenueService()
family_service = FamilyService()
household_service = HouseholdService()
education_training_service = EducationTrainingService()
employment_activity_service = EmploymentActivityService()
housing_service = HousingService()
population_structure_service = PopulationStructureService()
childcare_offer_service = ChildcareOfferService()
caf_benefits_service = CafBenefitsService()
revenues_poverty_service = RevenuesService()
schools_service = SchoolsService()
sixth_grade_service = SixthGradeService()
immigration_service = ImmigrationService()
childcare_service = ChildcareService()
public_safety_service = PublicSafetyService()
employment_service = EmploymentService()
schooling_service = SchoolingService()
family_employment_service = FamilyEmploymentService()

# 13. Créer un router protégé pour tous les autres endpoints
protected_router = APIRouter(dependencies=[Depends(get_current_user)])

# 14. Endpoints
@app.post("/token", response_model=Token)
# @limiter.limit(AUTH_RATE)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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

# Tous les endpoints existants, mais maintenant sur le router protégé
@protected_router.get("/")
@limiter.limit(DEFAULT_RATE)
async def root(request: Request):
    return {"message": "API Population 2021"}

@protected_router.get("/population/{code}",
    response_model=List[Population],
    summary="Obtenir la structure de la population d'une commune",
    description="Récupère la répartition détaillée de la population d'une commune par sexe et par âge (de 0 à 100 ans)",
    response_description="Liste détaillée des effectifs de population par sexe et âge")
@limiter.limit(HIGH_LOAD_RATE)
async def get_population_by_code(request: Request, code: str):
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
    summary="Obtenir les données des enfants de 0-5 ans pour une commune",
    description="Récupère les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour une commune",
    response_description="Les données démographiques incluant la population totale, le nombre d'enfants par tranche d'âge et leurs taux")
@limiter.limit(DEFAULT_RATE)
async def get_commune_children(request: Request, code: str):
    """
    Obtient les statistiques des enfants pour une commune :

    - **code**: Code INSEE de la commune
    """
    return population_service.get_population_and_children_rate(code)

@protected_router.get("/population/children/epci/{epci}",
    response_model=PopulationChildrenEPCI,
    summary="Obtenir les données des enfants de 0-5 ans pour un EPCI",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un EPCI",
    response_description="Les données démographiques incluant la population totale de l'EPCI, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
@limiter.limit(DEFAULT_RATE)
async def get_epci_children(request: Request, epci: str):
    """
    Agrège les statistiques des enfants pour un EPCI :

    - **epci**: Code de l'EPCI
    """
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@protected_router.get("/population/children/department/{dep}",
    response_model=PopulationChildrenDepartment,
    summary="Obtenir les données des enfants de 0-5 ans pour un département",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un département",
    response_description="Les données démographiques incluant la population totale du département, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
@limiter.limit(DEFAULT_RATE)
async def get_department_children(request: Request, dep: str):
    """
    Agrège les statistiques des enfants pour un département :

    - **dep**: Code du département
    """
    return population_service.aggregate_children_by_department(dep, geocode_service)

@protected_router.get("/population/children/region/{reg}",
    response_model=PopulationChildrenRegion,
    summary="Obtenir les données des enfants de 0-5 ans pour une région",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'une région",
    response_description="Les données démographiques incluant la population totale de la région, le nombre d'enfants par tranche d'âge, leurs taux, le nombre de communes et de départements")
@limiter.limit(DEFAULT_RATE)
async def get_region_children(request: Request, reg: str):
    """
    Agrège les statistiques des enfants pour une région :

    - **reg**: Code de la région
    """
    return population_service.aggregate_children_by_region(reg, geocode_service)

@protected_router.get("/population/children/france",
    response_model=PopulationChildrenFrance,
    summary="Obtenir les données des enfants de 0-5 ans pour la France entière",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour l'ensemble de la France",
    response_description="Les données démographiques incluant la population totale nationale, le nombre d'enfants par tranche d'âge, leurs taux, le nombre de communes, de départements et de régions")
@limiter.limit(DEFAULT_RATE)
async def get_france_children(request: Request):
    """
    Agrège les statistiques des enfants au niveau national
    """
    return population_service.aggregate_children_france(geocode_service)

@protected_router.get("/historical/{code}",
    response_model=List[HistoricalData],
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
@limiter.limit(DEFAULT_RATE)
async def get_historical_by_code(request: Request, code: str):
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
    summary="Obtenir les naissances par commune",
    description="Récupère les données historiques des naissances pour une commune spécifique",
    response_description="Les données de naissance annuelles pour la commune")
@limiter.limit(DEFAULT_RATE)
async def get_births_by_code(request: Request, code: str):
    """
    Récupère les données de naissance pour une commune :

    - **code**: Code INSEE de la commune
    """
    return birth_service.get_by_code(code)

@protected_router.get("/geocodes/epci/{epci}/births",
    summary="Obtenir les naissances agrégées par EPCI",
    description="Récupère et agrège les données de naissance pour toutes les communes d'un EPCI",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes et l'évolution par année")
@limiter.limit(DEFAULT_RATE)
async def get_epci_births(request: Request, epci: str):
    """
    Agrège les naissances au niveau EPCI :

    - **epci**: Code de l'EPCI
    """
    return geocode_service.aggregate_births_by_epci(epci, birth_service)

@protected_router.get("/geocodes/department/{dep}/births",
    summary="Obtenir les naissances agrégées par département",
    description="Récupère et agrège les données de naissance pour toutes les communes d'un département",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes et l'évolution par année")
@limiter.limit(DEFAULT_RATE)
async def get_department_births(request: Request, dep: str):
    """
    Agrège les naissances au niveau départemental :

    - **dep**: Code du département
    """
    return geocode_service.aggregate_births_by_department(dep, birth_service)

@protected_router.get("/geocodes/region/{reg}/births",
    summary="Obtenir les naissances agrégées par région",
    description="Récupère et agrège les données de naissance pour toutes les communes d'une région",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes, le nombre de départements et l'évolution par année")
@limiter.limit(DEFAULT_RATE)
async def get_region_births(request: Request, reg: str):
    """
    Agrège les naissances au niveau régional :

    - **reg**: Code de la région
    """
    return geocode_service.aggregate_births_by_region(reg, birth_service)

@protected_router.get("/geocodes/france/births",
    summary="Obtenir les naissances agrégées pour la France entière",
    description="Récupère et agrège les données de naissance pour toutes les communes de France",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes, le nombre de départements, le nombre de régions et l'évolution par année")
@limiter.limit(DEFAULT_RATE)
async def get_france_births(request: Request):
    """
    Agrège les naissances au niveau national
    """
    return geocode_service.aggregate_births_france(birth_service)

@protected_router.get("/revenues/median/commune/{code}",
    summary="Obtenir les revenus médians d'une commune",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'une commune depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour la commune")
@limiter.limit(DEFAULT_RATE)
async def get_commune_median_revenues(request: Request, code: str):
    """
    Obtient les données de revenus pour une commune :

    - **code**: Code INSEE de la commune

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues(code)

@protected_router.get("/revenues/median/epci/{code}",
    summary="Obtenir les revenus médians d'un EPCI",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'un EPCI depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour l'EPCI")
@limiter.limit(DEFAULT_RATE)
async def get_epci_median_revenues(request: Request, code: str):
    """
    Obtient les données de revenus agrégées pour un EPCI :

    - **code**: Code de l'EPCI

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages de l'EPCI
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_epci(code)

@protected_router.get("/revenues/median/department/{code}",
    summary="Obtenir les revenus médians d'un département",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'un département depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour le département")
@limiter.limit(DEFAULT_RATE)
async def get_department_median_revenues(request: Request, code: str):
    """
    Obtient les données de revenus agrégées pour un département :

    - **code**: Code du département

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages du département
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_department(code)

@protected_router.get("/revenues/median/region/{code}",
    summary="Obtenir les revenus médians d'une région",
    description="Récupère l'historique des revenus médians et des taux de pauvreté d'une région depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour la région")
@limiter.limit(DEFAULT_RATE)
async def get_region_median_revenues(request: Request, code: str):
    """
    Obtient les données de revenus agrégées pour une région :

    - **code**: Code de la région

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages de la région
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_region(code)

@protected_router.get("/revenues/median/france",
    summary="Obtenir les revenus médians de la France",
    description="Récupère l'historique des revenus médians et des taux de pauvreté au niveau national depuis 2017",
    response_description="Les revenus médians et taux de pauvreté par année pour la France entière")
@limiter.limit(DEFAULT_RATE)
async def get_france_median_revenues(request: Request):
    """
    Obtient les données de revenus agrégées au niveau national

    Retourne pour chaque année depuis 2017 :
    - Le revenu médian des ménages en France
    - Le taux de pauvreté (seuil à 60% du revenu médian)
    """
    return revenue_service.get_median_revenues_france()

import logging
from fastapi import Query
# Niveau de logs : INFO par défaut, DEBUG ponctuellement via `heroku config:set LOG_LEVEL=DEBUG`
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())

@protected_router.get("/childcare/commune/{code}",
    response_model=dict,
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
@limiter.limit(DEFAULT_RATE)
async def get_commune_childcare(
    request: Request,
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
    logging.debug(f"🔍 Requête reçue - code={code}, start_year={start_year}, end_year={end_year}")
    return childcare_service.get_coverage_by_commune(code, start_year, end_year)

@protected_router.get("/childcare/epci/{epci}",
    response_model=dict,
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
@limiter.limit(DEFAULT_RATE)
async def get_epci_childcare(
    request: Request,
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
@limiter.limit(DEFAULT_RATE)
async def get_department_childcare(
    request: Request,
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
@limiter.limit(DEFAULT_RATE)
async def get_region_childcare(
    request: Request,
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
@limiter.limit(DEFAULT_RATE)
async def get_france_childcare(
    request: Request,
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
    summary="Obtenir les statistiques des familles pour une commune",
    description="""Récupère l'évolution de la composition des familles pour une commune (millésimes 2012, 2017, 2023 — valeurs officielles INSEE).

Les données incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant
- Les familles nombreuses (3 enfants, 4 enfants ou plus)
- Les familles recomposées et traditionnelles (2023)
- Les taux correspondants

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
@limiter.limit(DEFAULT_RATE)
async def get_commune_families(
    request: Request,
    code: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles pour une commune :

    - **code**: Code INSEE de la commune
    - **start_year**: Année de début (optionnel, millésime 2012, 2017 ou 2023 ; défaut : millésime ≥ 5 ans avant le dernier)
    - **end_year**: Année de fin (optionnel, défaut : dernier millésime)
    """
    return family_service.get_families_by_commune(code, start_year, end_year)

@protected_router.get("/families/epci/{epci}",
    summary="Obtenir les statistiques des familles pour un EPCI",
    description="""Récupère l'évolution de la composition des familles pour un EPCI (millésimes 2012, 2017, 2023 — valeurs officielles INSEE).

Les données sont agrégées pour toutes les communes de l'EPCI et incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant
- Les familles nombreuses (3 enfants, 4 enfants ou plus)
- Les familles recomposées et traditionnelles (2023)
- Les taux correspondants

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
@limiter.limit(DEFAULT_RATE)
async def get_epci_families(
    request: Request,
    epci: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour un EPCI :

    - **epci**: Code de l'EPCI
    - **start_year**: Année de début (optionnel, millésime 2012, 2017 ou 2023 ; défaut : millésime ≥ 5 ans avant le dernier)
    - **end_year**: Année de fin (optionnel, défaut : dernier millésime)
    """
    return family_service.get_families_by_epci(epci, start_year, end_year)

@protected_router.get("/families/department/{dep}",
    summary="Obtenir les statistiques des familles pour un département",
    description="""Récupère l'évolution de la composition des familles pour un département (millésimes 2012, 2017, 2023 — valeurs officielles INSEE).

Les données sont agrégées pour toutes les communes du département et incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant
- Les familles nombreuses (3 enfants, 4 enfants ou plus)
- Les familles recomposées et traditionnelles (2023)
- Les taux correspondants

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
@limiter.limit(DEFAULT_RATE)
async def get_department_families(
    request: Request,
    dep: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour un département :

    - **dep**: Code du département
    - **start_year**: Année de début (optionnel, millésime 2012, 2017 ou 2023 ; défaut : millésime ≥ 5 ans avant le dernier)
    - **end_year**: Année de fin (optionnel, défaut : dernier millésime)
    """
    return family_service.get_families_by_department(dep, start_year, end_year)

@protected_router.get("/families/region/{reg}",
    summary="Obtenir les statistiques des familles pour une région",
    description="""Récupère l'évolution de la composition des familles pour une région (millésimes 2012, 2017, 2023 — valeurs officielles INSEE).

Les données sont agrégées pour toutes les communes de la région et incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant
- Les familles nombreuses (3 enfants, 4 enfants ou plus)
- Les familles recomposées et traditionnelles (2023)
- Les taux correspondants

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées.""")
@limiter.limit(DEFAULT_RATE)
async def get_region_families(
    request: Request,
    reg: str,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour une région :

    - **reg**: Code de la région
    - **start_year**: Année de début (optionnel, millésime 2012, 2017 ou 2023 ; défaut : millésime ≥ 5 ans avant le dernier)
    - **end_year**: Année de fin (optionnel, défaut : dernier millésime)
    """
    return family_service.get_families_by_region(reg, start_year, end_year)

@protected_router.get("/families/france",
    summary="Obtenir les statistiques des familles pour la France métropolitaine",
    description="""Récupère l'évolution de la composition des familles pour la France métropolitaine (millésimes 2012, 2017, 2023 — valeurs officielles INSEE).

Les données incluent pour chaque année :
- Le nombre total de familles
- Les couples avec enfant(s)
- Les familles monoparentales (détail père/mère)
- Les couples sans enfant
- Les familles nombreuses (3 enfants, 4 enfants ou plus)
- Les familles recomposées et traditionnelles (2023)
- Les taux correspondants

Les données sont accompagnées d'une analyse de l'évolution entre les années sélectionnées, permettant d'observer
les tendances démographiques nationales sur la structure des familles.""",
    response_description="Statistiques nationales annuelles avec analyse de l'évolution")
@limiter.limit(DEFAULT_RATE)
async def get_france_families(
    request: Request,
    start_year: int = None,
    end_year: int = None
):
    """
    Obtient les statistiques des familles agrégées pour la France métropolitaine :

    - **start_year**: Année de début (optionnel, millésime 2012, 2017 ou 2023 ; défaut : millésime ≥ 5 ans avant le dernier)
    - **end_year**: Année de fin (optionnel, défaut : dernier millésime)
    """
    return family_service.get_families_france(start_year, end_year)

@protected_router.get("/households/commune/{code}",
    summary="Obtenir la composition des ménages pour une commune",
    description="""Composition des ménages (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- nombre de ménages, population des ménages et taille moyenne
- types de ménages : personnes seules (hommes / femmes), sans famille, couples avec ou sans enfant(s), familles monoparentales
- ménages selon la catégorie socioprofessionnelle de la personne de référence
- personnes vivant seules par tranche d'âge (taux en % de la population des ménages du même âge)

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_commune_households(
    request: Request,
    code: str,
    start_year: int = None,
    end_year: int = None
):
    return household_service.get_households_by_commune(code, start_year, end_year)

@protected_router.get("/households/epci/{epci}",
    summary="Obtenir la composition des ménages pour un EPCI",
    description="""Composition des ménages (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- nombre de ménages, population des ménages et taille moyenne
- types de ménages : personnes seules (hommes / femmes), sans famille, couples avec ou sans enfant(s), familles monoparentales
- ménages selon la catégorie socioprofessionnelle de la personne de référence
- personnes vivant seules par tranche d'âge (taux en % de la population des ménages du même âge)

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_epci_households(
    request: Request,
    epci: str,
    start_year: int = None,
    end_year: int = None
):
    return household_service.get_households_by_epci(epci, start_year, end_year)

@protected_router.get("/households/department/{dep}",
    summary="Obtenir la composition des ménages pour un département",
    description="""Composition des ménages (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- nombre de ménages, population des ménages et taille moyenne
- types de ménages : personnes seules (hommes / femmes), sans famille, couples avec ou sans enfant(s), familles monoparentales
- ménages selon la catégorie socioprofessionnelle de la personne de référence
- personnes vivant seules par tranche d'âge (taux en % de la population des ménages du même âge)

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_department_households(
    request: Request,
    dep: str,
    start_year: int = None,
    end_year: int = None
):
    return household_service.get_households_by_department(dep, start_year, end_year)

@protected_router.get("/households/region/{reg}",
    summary="Obtenir la composition des ménages pour une région",
    description="""Composition des ménages (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- nombre de ménages, population des ménages et taille moyenne
- types de ménages : personnes seules (hommes / femmes), sans famille, couples avec ou sans enfant(s), familles monoparentales
- ménages selon la catégorie socioprofessionnelle de la personne de référence
- personnes vivant seules par tranche d'âge (taux en % de la population des ménages du même âge)

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_region_households(
    request: Request,
    reg: str,
    start_year: int = None,
    end_year: int = None
):
    return household_service.get_households_by_region(reg, start_year, end_year)

@protected_router.get("/households/france",
    summary="Obtenir la composition des ménages pour la France métropolitaine",
    description="""Composition des ménages (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- nombre de ménages, population des ménages et taille moyenne
- types de ménages : personnes seules (hommes / femmes), sans famille, couples avec ou sans enfant(s), familles monoparentales
- ménages selon la catégorie socioprofessionnelle de la personne de référence
- personnes vivant seules par tranche d'âge (taux en % de la population des ménages du même âge)

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_france_households(
    request: Request,
    start_year: int = None,
    end_year: int = None
):
    return household_service.get_households_france(start_year, end_year)

@protected_router.get("/education-training/commune/{code}",
    summary="Obtenir la scolarisation et les diplômes pour une commune",
    description="""Scolarisation et diplômes (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux de scolarisation à 2 ans et à 3-5 ans (2017, 2023) et par âge (2-5, 6-10, 11-14, 15-17, 18-24, 25-29 ans, 30 ans ou plus), par sexe pour 15-17 et 18-24 ans
- jeunes de 15-17 et 18-24 ans non scolarisés
- diplôme le plus élevé de la population de 15 ans ou plus non scolarisée (sans diplôme, brevet, CAP-BEP, bac, supérieur : bac+2, bac+3/4, bac+5 ou plus), par sexe pour « sans diplôme » et « supérieur »

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux. Bac+3/4 et bac+5 ne sont distingués qu'à partir de 2017 (bac+3 ou plus disponible pour les 3 millésimes).""")
@limiter.limit(DEFAULT_RATE)
async def get_commune_education_training(
    request: Request,
    code: str,
    start_year: int = None,
    end_year: int = None
):
    return education_training_service.by_commune(code, start_year, end_year)

@protected_router.get("/education-training/epci/{epci}",
    summary="Obtenir la scolarisation et les diplômes pour un EPCI",
    description="""Scolarisation et diplômes (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux de scolarisation à 2 ans et à 3-5 ans (2017, 2023) et par âge (2-5, 6-10, 11-14, 15-17, 18-24, 25-29 ans, 30 ans ou plus), par sexe pour 15-17 et 18-24 ans
- jeunes de 15-17 et 18-24 ans non scolarisés
- diplôme le plus élevé de la population de 15 ans ou plus non scolarisée (sans diplôme, brevet, CAP-BEP, bac, supérieur : bac+2, bac+3/4, bac+5 ou plus), par sexe pour « sans diplôme » et « supérieur »

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux. Bac+3/4 et bac+5 ne sont distingués qu'à partir de 2017 (bac+3 ou plus disponible pour les 3 millésimes).""")
@limiter.limit(DEFAULT_RATE)
async def get_epci_education_training(
    request: Request,
    epci: str,
    start_year: int = None,
    end_year: int = None
):
    return education_training_service.by_epci(epci, start_year, end_year)

@protected_router.get("/education-training/department/{dep}",
    summary="Obtenir la scolarisation et les diplômes pour un département",
    description="""Scolarisation et diplômes (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux de scolarisation à 2 ans et à 3-5 ans (2017, 2023) et par âge (2-5, 6-10, 11-14, 15-17, 18-24, 25-29 ans, 30 ans ou plus), par sexe pour 15-17 et 18-24 ans
- jeunes de 15-17 et 18-24 ans non scolarisés
- diplôme le plus élevé de la population de 15 ans ou plus non scolarisée (sans diplôme, brevet, CAP-BEP, bac, supérieur : bac+2, bac+3/4, bac+5 ou plus), par sexe pour « sans diplôme » et « supérieur »

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux. Bac+3/4 et bac+5 ne sont distingués qu'à partir de 2017 (bac+3 ou plus disponible pour les 3 millésimes).""")
@limiter.limit(DEFAULT_RATE)
async def get_department_education_training(
    request: Request,
    dep: str,
    start_year: int = None,
    end_year: int = None
):
    return education_training_service.by_department(dep, start_year, end_year)

@protected_router.get("/education-training/region/{reg}",
    summary="Obtenir la scolarisation et les diplômes pour une région",
    description="""Scolarisation et diplômes (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux de scolarisation à 2 ans et à 3-5 ans (2017, 2023) et par âge (2-5, 6-10, 11-14, 15-17, 18-24, 25-29 ans, 30 ans ou plus), par sexe pour 15-17 et 18-24 ans
- jeunes de 15-17 et 18-24 ans non scolarisés
- diplôme le plus élevé de la population de 15 ans ou plus non scolarisée (sans diplôme, brevet, CAP-BEP, bac, supérieur : bac+2, bac+3/4, bac+5 ou plus), par sexe pour « sans diplôme » et « supérieur »

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux. Bac+3/4 et bac+5 ne sont distingués qu'à partir de 2017 (bac+3 ou plus disponible pour les 3 millésimes).""")
@limiter.limit(DEFAULT_RATE)
async def get_region_education_training(
    request: Request,
    reg: str,
    start_year: int = None,
    end_year: int = None
):
    return education_training_service.by_region(reg, start_year, end_year)

@protected_router.get("/education-training/france",
    summary="Obtenir la scolarisation et les diplômes pour la France métropolitaine",
    description="""Scolarisation et diplômes (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux de scolarisation à 2 ans et à 3-5 ans (2017, 2023) et par âge (2-5, 6-10, 11-14, 15-17, 18-24, 25-29 ans, 30 ans ou plus), par sexe pour 15-17 et 18-24 ans
- jeunes de 15-17 et 18-24 ans non scolarisés
- diplôme le plus élevé de la population de 15 ans ou plus non scolarisée (sans diplôme, brevet, CAP-BEP, bac, supérieur : bac+2, bac+3/4, bac+5 ou plus), par sexe pour « sans diplôme » et « supérieur »

Évolution par défaut entre le dernier millésime et celui situé 5 à 6 ans plus tôt (2017 → 2023) ;
`difference` est exprimée en points pour les taux. Bac+3/4 et bac+5 ne sont distingués qu'à partir de 2017 (bac+3 ou plus disponible pour les 3 millésimes).""")
@limiter.limit(DEFAULT_RATE)
async def get_france_education_training(
    request: Request,
    start_year: int = None,
    end_year: int = None
):
    return education_training_service.france(start_year, end_year)

@protected_router.get("/employment-activity/commune/{code}",
    summary="Obtenir l'emploi et l'activité pour une commune",
    description="""Emploi et activité (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux d'activité, d'emploi et de chômage (au sens du recensement) par âge (15-64, 15-24, 25-54, 55-64 ans) et sexe ; écarts femmes-hommes
- inactivité des 15-64 ans : étudiants, retraités, personnes au foyer, autres inactifs
- chômage selon le diplôme (2023) et selon la catégorie socioprofessionnelle ; répartition des actifs par catégorie
- emploi au lieu de travail : indicateur de concentration d'emploi, secteurs d'activité, salariat, temps partiel, part des femmes
- mobilité domicile-travail : lieu de travail et mode de transport des actifs occupés

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_commune_employment_activity(
    request: Request,
    code: str,
    start_year: int = None,
    end_year: int = None
):
    return employment_activity_service.by_commune(code, start_year, end_year)

@protected_router.get("/employment-activity/epci/{epci}",
    summary="Obtenir l'emploi et l'activité pour un EPCI",
    description="""Emploi et activité (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux d'activité, d'emploi et de chômage (au sens du recensement) par âge (15-64, 15-24, 25-54, 55-64 ans) et sexe ; écarts femmes-hommes
- inactivité des 15-64 ans : étudiants, retraités, personnes au foyer, autres inactifs
- chômage selon le diplôme (2023) et selon la catégorie socioprofessionnelle ; répartition des actifs par catégorie
- emploi au lieu de travail : indicateur de concentration d'emploi, secteurs d'activité, salariat, temps partiel, part des femmes
- mobilité domicile-travail : lieu de travail et mode de transport des actifs occupés

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_epci_employment_activity(
    request: Request,
    epci: str,
    start_year: int = None,
    end_year: int = None
):
    return employment_activity_service.by_epci(epci, start_year, end_year)

@protected_router.get("/employment-activity/department/{dep}",
    summary="Obtenir l'emploi et l'activité pour un département",
    description="""Emploi et activité (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux d'activité, d'emploi et de chômage (au sens du recensement) par âge (15-64, 15-24, 25-54, 55-64 ans) et sexe ; écarts femmes-hommes
- inactivité des 15-64 ans : étudiants, retraités, personnes au foyer, autres inactifs
- chômage selon le diplôme (2023) et selon la catégorie socioprofessionnelle ; répartition des actifs par catégorie
- emploi au lieu de travail : indicateur de concentration d'emploi, secteurs d'activité, salariat, temps partiel, part des femmes
- mobilité domicile-travail : lieu de travail et mode de transport des actifs occupés

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_department_employment_activity(
    request: Request,
    dep: str,
    start_year: int = None,
    end_year: int = None
):
    return employment_activity_service.by_department(dep, start_year, end_year)

@protected_router.get("/employment-activity/region/{reg}",
    summary="Obtenir l'emploi et l'activité pour une région",
    description="""Emploi et activité (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux d'activité, d'emploi et de chômage (au sens du recensement) par âge (15-64, 15-24, 25-54, 55-64 ans) et sexe ; écarts femmes-hommes
- inactivité des 15-64 ans : étudiants, retraités, personnes au foyer, autres inactifs
- chômage selon le diplôme (2023) et selon la catégorie socioprofessionnelle ; répartition des actifs par catégorie
- emploi au lieu de travail : indicateur de concentration d'emploi, secteurs d'activité, salariat, temps partiel, part des femmes
- mobilité domicile-travail : lieu de travail et mode de transport des actifs occupés

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_region_employment_activity(
    request: Request,
    reg: str,
    start_year: int = None,
    end_year: int = None
):
    return employment_activity_service.by_region(reg, start_year, end_year)

@protected_router.get("/employment-activity/france",
    summary="Obtenir l'emploi et l'activité pour la France métropolitaine",
    description="""Emploi et activité (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- taux d'activité, d'emploi et de chômage (au sens du recensement) par âge (15-64, 15-24, 25-54, 55-64 ans) et sexe ; écarts femmes-hommes
- inactivité des 15-64 ans : étudiants, retraités, personnes au foyer, autres inactifs
- chômage selon le diplôme (2023) et selon la catégorie socioprofessionnelle ; répartition des actifs par catégorie
- emploi au lieu de travail : indicateur de concentration d'emploi, secteurs d'activité, salariat, temps partiel, part des femmes
- mobilité domicile-travail : lieu de travail et mode de transport des actifs occupés

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux.""")
@limiter.limit(DEFAULT_RATE)
async def get_france_employment_activity(
    request: Request,
    start_year: int = None,
    end_year: int = None
):
    return employment_activity_service.france(start_year, end_year)

HOUSING_DESCRIPTION = """Logement (INSEE, recensements 2012, 2017, 2023 — valeurs officielles) :
- parc : résidences principales, secondaires, logements vacants ; maisons et appartements
- statut d'occupation : propriétaires, locataires du parc privé, locataires HLM, meublés, logés gratuitement
- taille et peuplement : nombre de pièces, personnes par logement, suroccupation et sous-occupation
- mobilité résidentielle : ancienneté d'emménagement (emménagés récents, ancienneté moyenne par statut)
- conditions de vie : ménages sans voiture, stationnement, combustible de chauffage, période de construction

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux."""


@protected_router.get("/housing/commune/{code}", summary="Obtenir le logement pour une commune",
                      description=HOUSING_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_housing(request: Request, code: str, start_year: int = None, end_year: int = None):
    return housing_service.by_commune(code, start_year, end_year)


@protected_router.get("/housing/epci/{epci}", summary="Obtenir le logement pour un EPCI",
                      description=HOUSING_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_housing(request: Request, epci: str, start_year: int = None, end_year: int = None):
    return housing_service.by_epci(epci, start_year, end_year)


@protected_router.get("/housing/department/{dep}", summary="Obtenir le logement pour un département",
                      description=HOUSING_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_housing(request: Request, dep: str, start_year: int = None, end_year: int = None):
    return housing_service.by_department(dep, start_year, end_year)


@protected_router.get("/housing/region/{reg}", summary="Obtenir le logement pour une région",
                      description=HOUSING_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_housing(request: Request, reg: str, start_year: int = None, end_year: int = None):
    return housing_service.by_region(reg, start_year, end_year)


@protected_router.get("/housing/france", summary="Obtenir le logement pour la France métropolitaine",
                      description=HOUSING_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_housing(request: Request, start_year: int = None, end_year: int = None):
    return housing_service.france(start_year, end_year)

POPULATION_DESCRIPTION = """Population (INSEE, recensements — valeurs officielles) :
- structure par âge et sexe (2012, 2017, 2023) : jeunes, seniors, grand âge ; indice de vieillissement ; rapport de dépendance
- pyramide des âges par tranche de 5 ans et sexe, tranches de l'enfance et de la jeunesse (2023)
- catégories socioprofessionnelles des 15 ans ou plus, dont retraités
- mobilité résidentielle : lieu de résidence un an auparavant, âge des nouveaux arrivants
- `history` : série longue 1968 → 2023 (population, densité, logements) et, par période intercensitaire,
  taux de variation annuel moyen dû au solde naturel et au solde migratoire apparent, taux de natalité et de mortalité

Évolution par défaut 2017 → 2023 ; `difference` en points pour les taux."""


@protected_router.get("/population-structure/commune/{code}", summary="Obtenir la population d'une commune",
                      description=POPULATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_population_structure(request: Request, code: str, start_year: int = None, end_year: int = None):
    return population_structure_service.by_commune(code, start_year, end_year)


@protected_router.get("/population-structure/epci/{epci}", summary="Obtenir la population d'un EPCI",
                      description=POPULATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_population_structure(request: Request, epci: str, start_year: int = None, end_year: int = None):
    return population_structure_service.by_epci(epci, start_year, end_year)


@protected_router.get("/population-structure/department/{dep}", summary="Obtenir la population d'un département",
                      description=POPULATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_population_structure(request: Request, dep: str, start_year: int = None,
                                              end_year: int = None):
    return population_structure_service.by_department(dep, start_year, end_year)


@protected_router.get("/population-structure/region/{reg}", summary="Obtenir la population d'une région",
                      description=POPULATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_population_structure(request: Request, reg: str, start_year: int = None, end_year: int = None):
    return population_structure_service.by_region(reg, start_year, end_year)


@protected_router.get("/population-structure/france", summary="Obtenir la population de la France métropolitaine",
                      description=POPULATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_population_structure(request: Request, start_year: int = None, end_year: int = None):
    return population_structure_service.france(start_year, end_year)

CHILDCARE_OFFER_DESCRIPTION = """Accueil du jeune enfant (Cnaf, data.caf.fr — années 2017 à 2023) :
- nombre de places par mode d'accueil : accueil collectif (EAJE, PSU et hors PSU), préscolarisation,
  assistantes maternelles, garde à domicile ; répartition de l'offre
- taux de couverture (places pour 100 enfants de moins de 3 ans) par mode et global
- communes : celles publiées en détail par la Cnaf (environ 1 000) ; pour les autres, taux global 2020 et 2021
- France : France entière hors Mayotte (périmètre Cnaf)

Évolution par défaut : dernière année et année distante d'au moins 5 ans ; `difference` en points pour les taux."""


@protected_router.get("/childcare-offer/commune/{code}", summary="Accueil du jeune enfant d'une commune",
                      description=CHILDCARE_OFFER_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_childcare_offer(request: Request, code: str, start_year: int = None, end_year: int = None):
    return childcare_offer_service.by_commune(code, start_year, end_year)


@protected_router.get("/childcare-offer/epci/{epci}", summary="Accueil du jeune enfant d'un EPCI",
                      description=CHILDCARE_OFFER_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_childcare_offer(request: Request, epci: str, start_year: int = None, end_year: int = None):
    return childcare_offer_service.by_epci(epci, start_year, end_year)


@protected_router.get("/childcare-offer/department/{dep}", summary="Accueil du jeune enfant d'un département",
                      description=CHILDCARE_OFFER_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_childcare_offer(request: Request, dep: str, start_year: int = None, end_year: int = None):
    return childcare_offer_service.by_department(dep, start_year, end_year)


@protected_router.get("/childcare-offer/region/{reg}", summary="Accueil du jeune enfant d'une région",
                      description=CHILDCARE_OFFER_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_childcare_offer(request: Request, reg: str, start_year: int = None, end_year: int = None):
    return childcare_offer_service.by_region(reg, start_year, end_year)


@protected_router.get("/childcare-offer/france", summary="Accueil du jeune enfant en France (hors Mayotte)",
                      description=CHILDCARE_OFFER_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_childcare_offer(request: Request, start_year: int = None, end_year: int = None):
    return childcare_offer_service.france(start_year, end_year)

CAF_BENEFITS_DESCRIPTION = """Prestations CAF (Cnaf, data.caf.fr — foyers allocataires au 31 décembre, 2020 à 2024) :
- par prestation : foyers allocataires, personnes couvertes, montant mensuel versé (RSA, prime d'activité,
  aides au logement APL/ALF/ALS, allocations familiales, ASF, Paje, CMG, AAH, AEEH...)
- taux pour l'analyse des besoins sociaux, rapportés au recensement 2023 du territoire (`denominators`) :
  part des ménages allocataires et de la population couverte, population couverte par le RSA, la prime
  d'activité, les aides au logement, bénéficiaires de l'AAH pour 100 personnes de 20-64 ans, ASF pour
  100 familles monoparentales, montants moyens
- communes : sans les prestations liées au handicap (non publiées) ; régions et France métropolitaine :
  somme des départements

Évolution par défaut 2020 → 2024 ; `difference` en points pour les taux."""


@protected_router.get("/caf-benefits/commune/{code}", summary="Prestations CAF d'une commune",
                      description=CAF_BENEFITS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_caf_benefits(request: Request, code: str, start_year: int = None, end_year: int = None):
    return caf_benefits_service.by_commune(code, start_year, end_year)


@protected_router.get("/caf-benefits/epci/{epci}", summary="Prestations CAF d'un EPCI",
                      description=CAF_BENEFITS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_caf_benefits(request: Request, epci: str, start_year: int = None, end_year: int = None):
    return caf_benefits_service.by_epci(epci, start_year, end_year)


@protected_router.get("/caf-benefits/department/{dep}", summary="Prestations CAF d'un département",
                      description=CAF_BENEFITS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_caf_benefits(request: Request, dep: str, start_year: int = None, end_year: int = None):
    return caf_benefits_service.by_department(dep, start_year, end_year)


@protected_router.get("/caf-benefits/region/{reg}", summary="Prestations CAF d'une région",
                      description=CAF_BENEFITS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_caf_benefits(request: Request, reg: str, start_year: int = None, end_year: int = None):
    return caf_benefits_service.by_region(reg, start_year, end_year)


@protected_router.get("/caf-benefits/france", summary="Prestations CAF en France métropolitaine",
                      description=CAF_BENEFITS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_caf_benefits(request: Request, start_year: int = None, end_year: int = None):
    return caf_benefits_service.france(start_year, end_year)

REVENUES_POVERTY_DESCRIPTION = """Revenus et pauvreté (INSEE, Filosofi — 2017 à 2021 et 2023) :
- niveau de vie médian, déciles D1 et D9, rapport interdécile ; Gini et S80/S20 (2023, départements, régions, France)
- taux de pauvreté au seuil de 60 % : global, par âge du référent fiscal (2017-2021), par âge des individus dont
  moins de 18 ans (2023, départements, régions, France), par statut d'occupation du logement
- structure du revenu disponible (activité, chômage, pensions, patrimoine, prestations sociales, impôts)
- communes et EPCI 2023 : niveau de vie médian et taux de pauvreté seulement ; détail des communes soumis au
  secret statistique en deçà d'environ 1 000 ménages fiscaux

Évolution par défaut 2018 → 2023 ; `difference` en points pour les taux, en euros pour les niveaux de vie."""


@protected_router.get("/revenues-poverty/commune/{code}", summary="Revenus et pauvreté d'une commune",
                      description=REVENUES_POVERTY_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_revenues_poverty(request: Request, code: str, start_year: int = None, end_year: int = None):
    return revenues_poverty_service.by_commune(code, start_year, end_year)


@protected_router.get("/revenues-poverty/epci/{epci}", summary="Revenus et pauvreté d'un EPCI",
                      description=REVENUES_POVERTY_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_revenues_poverty(request: Request, epci: str, start_year: int = None, end_year: int = None):
    return revenues_poverty_service.by_epci(epci, start_year, end_year)


@protected_router.get("/revenues-poverty/department/{dep}", summary="Revenus et pauvreté d'un département",
                      description=REVENUES_POVERTY_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_revenues_poverty(request: Request, dep: str, start_year: int = None, end_year: int = None):
    return revenues_poverty_service.by_department(dep, start_year, end_year)


@protected_router.get("/revenues-poverty/region/{reg}", summary="Revenus et pauvreté d'une région",
                      description=REVENUES_POVERTY_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_revenues_poverty(request: Request, reg: str, start_year: int = None, end_year: int = None):
    return revenues_poverty_service.by_region(reg, start_year, end_year)


@protected_router.get("/revenues-poverty/france", summary="Revenus et pauvreté en France métropolitaine",
                      description=REVENUES_POVERTY_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_revenues_poverty(request: Request, start_year: int = None, end_year: int = None):
    return revenues_poverty_service.france(start_year, end_year)

SCHOOLS_DESCRIPTION = """Établissements scolaires (ministère de l'Éducation nationale, DEPP) d'une commune ou d'un EPCI :
écoles, collèges et lycées, avec pour chacun et par année :
- l'indice de position sociale (IPS), son décile et son centile parmi les établissements du même type en France
  (écoles ; collèges ; lycées LEGT, LPO, LP — public et privé sous contrat), les IPS de référence
- collèges : DNB (taux de réussite, note à l'écrit), valeurs ajoutées et leur centile national, accès 6e-3e
- lycées : bac général et technologique / professionnel, valeurs ajoutées (réussite, accès de la 2nde au bac, mentions)
- l'indice d'éloignement (collèges, lycées ; base 100, plus élevé = plus éloigné des ressources), son décile

`year` = année de rentrée pour l'IPS et l'éloignement (2025 = 2025-2026), année de session pour les examens.
`national` : distribution nationale (moyenne, déciles D1-D9) de chaque indicateur par type et par année."""


@protected_router.get("/schools/commune/{code}", summary="Établissements scolaires d'une commune",
                      description=SCHOOLS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_schools(request: Request, code: str):
    return schools_service.by_commune(code)


@protected_router.get("/schools/epci/{epci}", summary="Établissements scolaires d'un EPCI",
                      description=SCHOOLS_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_schools(request: Request, epci: str):
    return schools_service.by_epci(epci)


SIXTH_GRADE_DESCRIPTION = """Âge des élèves à l'entrée en 6e (DEPP), 2020 à 2025 : élèves à l'heure, en avance, en retard,
par sexe et par secteur ; taux de retard (late_rate). Publié par département ; régions et France métropolitaine
('FM') obtenues par somme des départements."""


@protected_router.get("/sixth-grade/department/{dep}", summary="Retard à l'entrée en 6e d'un département",
                      description=SIXTH_GRADE_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_sixth_grade(request: Request, dep: str, start_year: int = None, end_year: int = None):
    return sixth_grade_service.by_department(dep, start_year, end_year)


@protected_router.get("/sixth-grade/region/{reg}", summary="Retard à l'entrée en 6e d'une région",
                      description=SIXTH_GRADE_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_sixth_grade(request: Request, reg: str, start_year: int = None, end_year: int = None):
    return sixth_grade_service.by_region(reg, start_year, end_year)


@protected_router.get("/sixth-grade/france", summary="Retard à l'entrée en 6e en France métropolitaine",
                      description=SIXTH_GRADE_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_sixth_grade(request: Request, start_year: int = None, end_year: int = None):
    return sixth_grade_service.france(start_year, end_year)

IMMIGRATION_DESCRIPTION = """Immigrés et étrangers (INSEE, recensement 2023) :
- part des immigrés (nés étrangers à l'étranger) et des étrangers (sans la nationalité française) dans la population
- âge : part des 55 ans ou plus parmi les immigrés, part des immigrés parmi les 55 ans ou plus
- emploi : chômage des immigrés / non-immigrés et des étrangers / Français (15 ans ou plus), taux d'emploi des
  25-54 ans et des femmes de 25-54 ans, part des femmes de 25-54 ans au foyer
- part des ouvriers et employés (exploitation complémentaire)
Effectifs issus du recensement (estimations) : à manier avec prudence en dessous de 200 personnes."""


@protected_router.get("/immigration/commune/{code}", summary="Immigrés et étrangers d'une commune",
                      description=IMMIGRATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_commune_immigration(request: Request, code: str):
    return immigration_service.by_commune(code)


@protected_router.get("/immigration/epci/{epci}", summary="Immigrés et étrangers d'un EPCI",
                      description=IMMIGRATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_epci_immigration(request: Request, epci: str):
    return immigration_service.by_epci(epci)


@protected_router.get("/immigration/department/{dep}", summary="Immigrés et étrangers d'un département",
                      description=IMMIGRATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_department_immigration(request: Request, dep: str):
    return immigration_service.by_department(dep)


@protected_router.get("/immigration/region/{reg}", summary="Immigrés et étrangers d'une région",
                      description=IMMIGRATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_region_immigration(request: Request, reg: str):
    return immigration_service.by_region(reg)


@protected_router.get("/immigration/france", summary="Immigrés et étrangers en France métropolitaine",
                      description=IMMIGRATION_DESCRIPTION)
@limiter.limit(DEFAULT_RATE)
async def get_france_immigration(request: Request):
    return immigration_service.france()

@protected_router.get("/public-safety/commune/{code}",
   response_model=PublicSafetyResponse,
   summary="Obtenir les indicateurs de sécurité d'une commune",
   description="""Récupère les indicateurs de sécurité publique pour une commune et ses territoires parents (département et région).

Les données incluent pour chaque année :
- Les taux d'atteintes aux personnes
- Les taux d'atteintes aux biens
- Les taux de violences intrafamiliales
- Les taux d'infractions économiques et financières

Les données communales sont comparées avec celles du département et de la région pour permettre une mise en perspective territoriale.""",
   response_description="Indicateurs de sécurité communaux, départementaux et régionaux")
@limiter.limit(DEFAULT_RATE)
async def get_commune_public_safety(request: Request, code: str):
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
    summary="Obtenir les indicateurs de sécurité d'un département",
    description="""Récupère les indicateurs de sécurité publique pour un département et sa région parente.

Les données incluent pour chaque année :
- Les taux d'atteintes aux personnes
- Les taux d'atteintes aux biens
- Les taux de violences intrafamiliales
- Les taux d'infractions économiques et financières

Les données départementales sont comparées avec celles de la région parente.""",
    response_description="Indicateurs de sécurité départementaux et régionaux")
@limiter.limit(DEFAULT_RATE)
async def get_department_public_safety(request: Request, dep: str):
    """
    Obtient les indicateurs de sécurité pour un département :

    - **dep**: Code du département
    """
    return public_safety_service.get_by_department(dep)

@protected_router.get("/public-safety/region/{reg}",
    response_model=PublicSafetyResponse,
    summary="Obtenir les indicateurs de sécurité d'une région",
    description="""Récupère les indicateurs de sécurité publique pour une région.

Les données incluent pour chaque année :
- Les taux d'atteintes aux personnes
- Les taux d'atteintes aux biens
- Les taux de violences intrafamiliales
- Les taux d'infractions économiques et financières""",
    response_description="Indicateurs de sécurité régionaux")
@limiter.limit(DEFAULT_RATE)
async def get_region_public_safety(request: Request, reg: str):
    """
    Obtient les indicateurs de sécurité pour une région :

    - **reg**: Code de la région
    """
    return public_safety_service.get_by_region(reg)

@protected_router.get("/employment/rates/commune/{code}",
    response_model=EmploymentResponse,
    summary="Obtenir les taux d'emploi des femmes pour une commune",
    description="""Récupère les indicateurs d'emploi des femmes pour une commune en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes de la commune")
@limiter.limit(DEFAULT_RATE)
async def get_commune_employment_rates(request: Request, code: str):
    """
    Obtient les statistiques d'emploi des femmes pour une commune :

    - **code**: Code INSEE de la commune
    """
    return employment_service.get_commune_rates(code)

@protected_router.get("/employment/rates/epci/{epci}",
    response_model=EmploymentResponse,
    summary="Obtenir les taux d'emploi des femmes pour un EPCI",
    description="""Récupère les indicateurs d'emploi des femmes agrégés pour un EPCI (Établissement Public de Coopération Intercommunale) en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes agrégés pour l'EPCI")
@limiter.limit(DEFAULT_RATE)
async def get_epci_employment_rates(request: Request, epci: str):
    """
    Obtient les statistiques d'emploi des femmes agrégées pour un EPCI :

    - **epci**: Code de l'EPCI
    """
    return employment_service.get_epci_rates(epci)

@protected_router.get("/employment/rates/department/{dep}",
    response_model=EmploymentResponse,
    summary="Obtenir les taux d'emploi des femmes pour un département",
    description="""Récupère les indicateurs d'emploi des femmes agrégés pour un département en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes agrégés pour le département")
@limiter.limit(DEFAULT_RATE)
async def get_department_employment_rates(request: Request, dep: str):
    """
    Obtient les statistiques d'emploi des femmes agrégées pour un département :

    - **dep**: Code du département
    """
    return employment_service.get_department_rates(dep)

@protected_router.get("/employment/rates/region/{reg}",
    response_model=EmploymentResponse,
    summary="Obtenir les taux d'emploi des femmes pour une région",
    description="""Récupère les indicateurs d'emploi des femmes agrégés pour une région en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes agrégés pour la région")
@limiter.limit(DEFAULT_RATE)
async def get_region_employment_rates(request: Request, reg: str):
    """
    Obtient les statistiques d'emploi des femmes agrégées pour une région :

    - **reg**: Code de la région
    """
    return employment_service.get_region_rates(reg)

@protected_router.get("/employment/rates/france",
    response_model=EmploymentResponse,
    summary="Obtenir les taux d'emploi des femmes pour la France",
    description="""Récupère les indicateurs d'emploi des femmes au niveau national en 2021.

Les données incluent :
- Taux d'activité (femmes actives / population totale)
- Taux d'emploi (femmes ayant un emploi / population totale)
- Taux de temps partiel pour les 25-54 ans
- Taux de temps partiel pour les 15-64 ans""",
    response_description="Indicateurs d'emploi des femmes au niveau national")
@limiter.limit(DEFAULT_RATE)
async def get_france_employment_rates(request: Request):
    """
    Obtient les statistiques d'emploi des femmes au niveau national
    """
    return employment_service.get_france_rates()

@protected_router.get("/education/schooling/commune/{code}",
   response_model=SchoolingResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_commune_schooling(request: Request, code: str):
   """
   Obtient les taux de scolarisation pour une commune :

   - **code**: Code INSEE de la commune
   """
   return schooling_service.get_commune_schooling(code)

@protected_router.get("/education/schooling/epci/{epci}",
   response_model=SchoolingResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_epci_schooling(request: Request, epci: str):
   """
   Obtient les taux de scolarisation agrégés pour un EPCI :

   - **epci**: Code de l'EPCI
   """
   return schooling_service.get_epci_schooling(epci)

@protected_router.get("/education/schooling/department/{dep}",
   response_model=SchoolingResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_department_schooling(request: Request, dep: str):
   """
   Obtient les taux de scolarisation agrégés pour un département :

   - **dep**: Code du département
   """
   return schooling_service.get_department_schooling(dep)

@protected_router.get("/education/schooling/region/{reg}",
   response_model=SchoolingResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_region_schooling(request: Request, reg: str):
   """
   Obtient les taux de scolarisation agrégés pour une région :

   - **reg**: Code de la région
   """
   return schooling_service.get_region_schooling(reg)

@protected_router.get("/education/schooling/france",
   response_model=SchoolingResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_france_schooling(request: Request):
   """
   Obtient les taux de scolarisation au niveau national
   """
   return schooling_service.get_france_schooling()

# Routes pour les 0-2 ans
@protected_router.get("/families/employment/under3/commune/{code}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_commune_family_employment_under3(request: Request, code: str):
   """
   Obtient la répartition des situations d'emploi pour une commune :

   - **code**: Code INSEE de la commune
   """
   return family_employment_service.get_commune_distribution(code, age_group="0")

@protected_router.get("/families/employment/under3/epci/{epci}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_epci_family_employment_under3(request: Request, epci: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un EPCI :

   - **epci**: Code de l'EPCI
   """
   return family_employment_service.get_epci_distribution(epci, age_group="0")

@protected_router.get("/families/employment/under3/department/{dep}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_department_family_employment_under3(request: Request, dep: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un département :

   - **dep**: Code du département
   """
   return family_employment_service.get_department_distribution(dep, age_group="0")

@protected_router.get("/families/employment/under3/region/{reg}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_region_family_employment_under3(request: Request, reg: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour une région :

   - **reg**: Code de la région
   """
   return family_employment_service.get_region_distribution(reg, age_group="0")

@protected_router.get("/families/employment/under3/france",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_france_family_employment_under3(request: Request):
   """
   Obtient la répartition des situations d'emploi au niveau national
   """
   return family_employment_service.get_france_distribution(age_group="0")

# Routes pour les 3-5 ans
@protected_router.get("/families/employment/3to5/commune/{code}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_commune_family_employment_3to5(request: Request, code: str):
   """
   Obtient la répartition des situations d'emploi pour une commune :

   - **code**: Code INSEE de la commune
   """
   return family_employment_service.get_commune_distribution(code, age_group="3")

@protected_router.get("/families/employment/3to5/epci/{epci}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_epci_family_employment_3to5(request: Request, epci: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un EPCI :

   - **epci**: Code de l'EPCI
   """
   return family_employment_service.get_epci_distribution(epci, age_group="3")

@protected_router.get("/families/employment/3to5/department/{dep}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_department_family_employment_3to5(request: Request, dep: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour un département :

   - **dep**: Code du département
   """
   return family_employment_service.get_department_distribution(dep, age_group="3")

@protected_router.get("/families/employment/3to5/region/{reg}",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_region_family_employment_3to5(request: Request, reg: str):
   """
   Obtient la répartition agrégée des situations d'emploi pour une région :

   - **reg**: Code de la région
   """
   return family_employment_service.get_region_distribution(reg, age_group="3")

@protected_router.get("/families/employment/3to5/france",
   response_model=FamilyEmploymentResponse,
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
@limiter.limit(DEFAULT_RATE)
async def get_france_family_employment_3to5(request: Request):
   """
   Obtient la répartition des situations d'emploi au niveau national
   """
   return family_employment_service.get_france_distribution(age_group="3")

@protected_router.get("/families/{level}/{code}",
  summary="Obtenir l'évolution de la composition des familles par niveau géographique",
  description="""Récupère l'évolution historique de la composition des familles (millésimes 2012, 2017, 2023 — valeurs officielles INSEE) pour le niveau géographique choisi.

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
- Les familles nombreuses (3 enfants, 4 enfants ou plus)
- Les familles recomposées et traditionnelles (2023)
- Les taux correspondants

L'évolution est calculée entre les années spécifiées (start_year et end_year) et indique pour chaque catégorie :
- La valeur de départ
- La valeur finale
- Le pourcentage d'évolution
- La période concernée""")
@limiter.limit(DEFAULT_RATE)
async def get_families(
   request: Request,
   level: str,
   code: str,
   start_year: int = None,
   end_year: int = None
):
   """
   Obtient l'évolution de la composition des familles pour un territoire :

   - **level**: Niveau géographique ('commune', 'epci', 'department' ou 'region')
   - **code**: Code du territoire (INSEE, EPCI, département ou région)
   - **start_year**: Année de début pour le calcul de l'évolution (optionnel, millésime 2012, 2017 ou 2023 ; défaut : millésime ≥ 5 ans avant le dernier)
   - **end_year**: Année de fin pour le calcul de l'évolution (optionnel, défaut : dernier millésime)
   """
   if level == "commune":
       return family_service.get_families_by_commune(code, start_year, end_year)
   elif level == "epci":
       return family_service.get_families_by_epci(code, start_year, end_year)
   elif level == "department":
       return family_service.get_families_by_department(code, start_year, end_year)
   elif level == "region":
       return family_service.get_families_by_region(code, start_year, end_year)
   else:
       raise HTTPException(status_code=404, detail=f"Level {level} not found")

# Inclure le router protégé dans l'app
app.include_router(protected_router)
