from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from .services.population_service import PopulationService
from .services.historical_service import HistoricalService
from .services.birth_service import BirthService
from .services.geocode_service import GeoCodeService
from .services.revenue_service import RevenueService
from .services.family_service import FamilyService
from .services.childcare_service import ChildcareService
from .services.large_family_service import LargeFamilyService
from .services.public_safety_service import PublicSafetyService
from .services.employment_service import EmploymentService
from .services.schooling_service import SchoolingService
from .services.family_employment_service import FamilyEmploymentService
from .models import Population, HistoricalData, PopulationChildrenRate, PopulationChildrenEPCI, PopulationChildrenDepartment, PopulationChildrenRegion, PopulationChildrenFrance, Birth, Revenue, Family, Childcare, LargeFamilyResponse, PublicSafetyResponse, EmploymentResponse, SchoolingResponse, SchoolingData, FamilyEmploymentResponse, FamilyEmploymentDistribution

app = FastAPI(title="API Population")
app.mount("/static", StaticFiles(directory="static"), name="static")
population_service = PopulationService()
historical_service = HistoricalService()
birth_service = BirthService()
geocode_service = GeoCodeService()
revenue_service = RevenueService()
family_service = FamilyService()
childcare_service = ChildcareService()
large_family_service = LargeFamilyService()
public_safety_service = PublicSafetyService()
employment_service = EmploymentService()
schooling_service = SchoolingService()
family_employment_service = FamilyEmploymentService()


@app.get("/")
async def root():
    return {"message": "API Population 2021"}

@app.get("/population/{code}",
    response_model=List[Population],
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

@app.get("/population/children/commune/{code}",
    response_model=PopulationChildrenRate,
    summary="Obtenir les données des enfants de 0-5 ans pour une commune",
    description="Récupère les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour une commune",
    response_description="Les données démographiques incluant la population totale, le nombre d'enfants par tranche d'âge et leurs taux")
async def get_commune_children(code: str):
    """
    Obtient les statistiques des enfants pour une commune :

    - **code**: Code INSEE de la commune
    """
    return population_service.get_population_and_children_rate(code)

@app.get("/population/children/epci/{epci}",
    response_model=PopulationChildrenEPCI,
    summary="Obtenir les données des enfants de 0-5 ans pour un EPCI",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un EPCI",
    response_description="Les données démographiques incluant la population totale de l'EPCI, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
async def get_epci_children(epci: str):
    """
    Agrège les statistiques des enfants pour un EPCI :

    - **epci**: Code de l'EPCI
    """
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@app.get("/population/children/department/{dep}",
    response_model=PopulationChildrenDepartment,
    summary="Obtenir les données des enfants de 0-5 ans pour un département",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un département",
    response_description="Les données démographiques incluant la population totale du département, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
async def get_department_children(dep: str):
    """
    Agrège les statistiques des enfants pour un département :

    - **dep**: Code du département
    """
    return population_service.aggregate_children_by_department(dep, geocode_service)

@app.get("/population/children/region/{reg}",
    response_model=PopulationChildrenRegion,
    summary="Obtenir les données des enfants de 0-5 ans pour une région",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'une région",
    response_description="Les données démographiques incluant la population totale de la région, le nombre d'enfants par tranche d'âge, leurs taux, le nombre de communes et de départements")
async def get_region_children(reg: str):
    """
    Agrège les statistiques des enfants pour une région :

    - **reg**: Code de la région
    """
    return population_service.aggregate_children_by_region(reg, geocode_service)

@app.get("/population/children/france",
    response_model=PopulationChildrenFrance,
    summary="Obtenir les données des enfants de 0-5 ans pour la France entière",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour l'ensemble de la France",
    response_description="Les données démographiques incluant la population totale nationale, le nombre d'enfants par tranche d'âge, leurs taux, le nombre de communes, de départements et de régions")
async def get_france_children():
    """
    Agrège les statistiques des enfants au niveau national
    """
    return population_service.aggregate_children_france(geocode_service)

@app.get("/historical/{code}", response_model=List[HistoricalData])
async def get_historical_by_code(code: str):
    return historical_service.get_by_code(code)


@app.get("/geocodes/{code}")
async def get_geocode(code: str):
   return geocode_service.get_by_code(code)

@app.get("/geocodes/region/{reg}")
async def get_by_region(reg: str):
   return geocode_service.get_by_region(reg)

@app.get("/geocodes/department/{dep}")
async def get_by_department(dep: str):
   return geocode_service.get_by_department(dep)

@app.get("/births/{code}", response_model=List[Birth],
    summary="Obtenir les naissances par commune",
    description="Récupère les données historiques des naissances pour une commune spécifique",
    response_description="Les données de naissance annuelles pour la commune")
async def get_births_by_code(code: str):
    """
    Récupère les données de naissance pour une commune :

    - **code**: Code INSEE de la commune
    """
    return birth_service.get_by_code(code)

@app.get("/geocodes/epci/{epci}/births",
    summary="Obtenir les naissances agrégées par EPCI",
    description="Récupère et agrège les données de naissance pour toutes les communes d'un EPCI",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes et l'évolution par année")
async def get_epci_births(epci: str):
    """
    Agrège les naissances au niveau EPCI :

    - **epci**: Code de l'EPCI
    """
    return geocode_service.aggregate_births_by_epci(epci, birth_service)

@app.get("/geocodes/department/{dep}/births",
    summary="Obtenir les naissances agrégées par département",
    description="Récupère et agrège les données de naissance pour toutes les communes d'un département",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes et l'évolution par année")
async def get_department_births(dep: str):
    """
    Agrège les naissances au niveau départemental :

    - **dep**: Code du département
    """
    return geocode_service.aggregate_births_by_department(dep, birth_service)

@app.get("/geocodes/region/{reg}/births",
    summary="Obtenir les naissances agrégées par région",
    description="Récupère et agrège les données de naissance pour toutes les communes d'une région",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes, le nombre de départements et l'évolution par année")
async def get_region_births(reg: str):
    """
    Agrège les naissances au niveau régional :

    - **reg**: Code de la région
    """
    return geocode_service.aggregate_births_by_region(reg, birth_service)

@app.get("/geocodes/france/births",
    summary="Obtenir les naissances agrégées pour la France entière",
    description="Récupère et agrège les données de naissance pour toutes les communes de France",
    response_description="Les données de naissance agrégées incluant le nombre total de naissances, le nombre de communes, le nombre de départements, le nombre de régions et l'évolution par année")
async def get_france_births():
    """
    Agrège les naissances au niveau national
    """
    return geocode_service.aggregate_births_france(birth_service)

@app.get("/revenues/median/commune/{code}",
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

@app.get("/revenues/median/epci/{code}",
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

@app.get("/revenues/median/department/{code}",
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

@app.get("/revenues/median/region/{code}",
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

@app.get("/revenues/median/france",
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

@app.get("/revenues/median/iris/{commune}")
async def get_iris_median_revenues(commune: str):
    return revenue_service.get_iris_revenues_by_commune(commune, geocode_service)

@app.get("/childcare/commune/{code}", response_model=dict)
async def get_commune_childcare(code: str, start_year: int = None, end_year: int = None):
    return childcare_service.get_coverage_by_commune(code, start_year, end_year)

@app.get("/childcare/epci/{epci}", response_model=dict)
async def get_epci_childcare(epci: str, start_year: int = None, end_year: int = None):
    return childcare_service.get_coverage_by_epci(epci, start_year, end_year)

@app.get("/childcare/department/{dep}", response_model=dict)
async def get_department_childcare(dep: str, start_year: int = None, end_year: int = None):
    return childcare_service.get_coverage_by_department(dep, start_year, end_year)

@app.get("/childcare/region/{reg}", response_model=dict)
async def get_region_childcare(reg: str, start_year: int = None, end_year: int = None):
    return childcare_service.get_coverage_by_region(reg, start_year, end_year)

@app.get("/childcare/france", response_model=dict)
async def get_france_childcare(start_year: int = None, end_year: int = None):
    return childcare_service.get_coverage_france(start_year, end_year)

@app.get("/families/large/commune/{code}", response_model=LargeFamilyResponse)
async def get_commune_large_families(code: str):
    return large_family_service.get_large_families_by_commune(code)

@app.get("/families/large/epci/{epci}", response_model=LargeFamilyResponse)
async def get_epci_large_families(epci: str):
    return large_family_service.get_large_families_by_epci(epci, geocode_service)

@app.get("/families/large/department/{dep}", response_model=LargeFamilyResponse)
async def get_department_large_families(dep: str):
    return large_family_service.get_large_families_by_department(dep, geocode_service)

@app.get("/families/large/region/{reg}", response_model=LargeFamilyResponse)
async def get_region_large_families(reg: str):
    return large_family_service.get_large_families_by_region(reg, geocode_service)

@app.get("/families/large/france", response_model=LargeFamilyResponse)
async def get_france_large_families():
    return large_family_service.get_large_families_france()

@app.get("/families/iris/{commune}")
async def get_iris_families(commune: str):
    return family_service.get_iris_families_by_commune(commune, geocode_service)

@app.get("/families/france")
async def get_france_families(start_year: int = None, end_year: int = None):
    return family_service.get_families_france(start_year, end_year)

@app.get("/public-safety/commune/{code}", response_model=PublicSafetyResponse)
async def get_commune_public_safety(code: str):
    return public_safety_service.get_by_commune(code)

@app.get("/employment/rates/commune/{code}", response_model=EmploymentResponse)
async def get_commune_employment_rates(code: str):
    return employment_service.get_commune_rates(code)

@app.get("/employment/rates/epci/{epci}", response_model=EmploymentResponse)
async def get_epci_employment_rates(epci: str):
    return employment_service.get_epci_rates(epci)

@app.get("/employment/rates/department/{dep}", response_model=EmploymentResponse)
async def get_department_employment_rates(dep: str):
    return employment_service.get_department_rates(dep)

@app.get("/employment/rates/region/{reg}", response_model=EmploymentResponse)
async def get_region_employment_rates(reg: str):
    return employment_service.get_region_rates(reg)

@app.get("/employment/rates/france", response_model=EmploymentResponse)
async def get_france_employment_rates():
    return employment_service.get_france_rates()

@app.get("/education/schooling/commune/{code}", response_model=SchoolingResponse)
async def get_commune_schooling(code: str):
    return schooling_service.get_commune_schooling(code)

@app.get("/education/schooling/epci/{epci}", response_model=SchoolingResponse)
async def get_epci_schooling(epci: str):
    return schooling_service.get_epci_schooling(epci)

@app.get("/education/schooling/department/{dep}", response_model=SchoolingResponse)
async def get_department_schooling(dep: str):
    return schooling_service.get_department_schooling(dep)

@app.get("/education/schooling/region/{reg}", response_model=SchoolingResponse)
async def get_region_schooling(reg: str):
    return schooling_service.get_region_schooling(reg)

@app.get("/education/schooling/france", response_model=SchoolingResponse)
async def get_france_schooling():
    return schooling_service.get_france_schooling()

# Routes pour les 0-2 ans
@app.get("/families/employment/under3/commune/{code}", response_model=FamilyEmploymentResponse)
async def get_commune_family_employment_under3(code: str):
    return family_employment_service.get_commune_distribution(code, age_group=0)

@app.get("/families/employment/under3/epci/{epci}", response_model=FamilyEmploymentResponse)
async def get_epci_family_employment_under3(epci: str):
    return family_employment_service.get_epci_distribution(epci, age_group=0)

@app.get("/families/employment/under3/department/{dep}", response_model=FamilyEmploymentResponse)
async def get_department_family_employment_under3(dep: str):
    return family_employment_service.get_department_distribution(dep, age_group=0)

@app.get("/families/employment/under3/region/{reg}", response_model=FamilyEmploymentResponse)
async def get_region_family_employment_under3(reg: str):
    return family_employment_service.get_region_distribution(reg, age_group=0)

@app.get("/families/employment/under3/france", response_model=FamilyEmploymentResponse)
async def get_france_family_employment_under3():
    return family_employment_service.get_france_distribution(age_group=0)

# Routes pour les 3-5 ans
@app.get("/families/employment/3to5/commune/{code}", response_model=FamilyEmploymentResponse)
async def get_commune_family_employment_3to5(code: str):
    return family_employment_service.get_commune_distribution(code, age_group=3)

@app.get("/families/employment/3to5/epci/{epci}", response_model=FamilyEmploymentResponse)
async def get_epci_family_employment_3to5(epci: str):
    return family_employment_service.get_epci_distribution(epci, age_group=3)

@app.get("/families/employment/3to5/department/{dep}", response_model=FamilyEmploymentResponse)
async def get_department_family_employment_3to5(dep: str):
    return family_employment_service.get_department_distribution(dep, age_group=3)

@app.get("/families/employment/3to5/region/{reg}", response_model=FamilyEmploymentResponse)
async def get_region_family_employment_3to5(reg: str):
    return family_employment_service.get_region_distribution(reg, age_group=3)

@app.get("/families/employment/3to5/france", response_model=FamilyEmploymentResponse)
async def get_france_family_employment_3to5():
    return family_employment_service.get_france_distribution(age_group=3)

@app.get("/families/{level}/{code}")
async def get_families(level: str, code: str, start_year: int = None, end_year: int = None):
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
