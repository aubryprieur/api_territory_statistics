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

@app.get("/population/{code}", response_model=List[Population])
async def get_population_by_code(code: str):
    data = population_service.get_by_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Code non trouvé")
    return data


@app.get("/population/children/commune/{code}", response_model=PopulationChildrenRate)
async def get_commune_children(code: str):
    return population_service.get_population_and_children_rate(code)

@app.get("/population/children/epci/{epci}", response_model=PopulationChildrenEPCI)
async def get_epci_children(epci: str):
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@app.get("/population/children/department/{dep}", response_model=PopulationChildrenDepartment)
async def get_department_children(dep: str):
    return population_service.aggregate_children_by_department(dep, geocode_service)

@app.get("/population/children/region/{reg}", response_model=PopulationChildrenRegion)
async def get_region_children(reg: str):
    return population_service.aggregate_children_by_region(reg, geocode_service)

@app.get("/population/children/france", response_model=PopulationChildrenFrance)
async def get_france_children():
    return population_service.aggregate_children_france(geocode_service)

@app.get("/historical/{code}", response_model=List[HistoricalData])
async def get_historical_by_code(code: str):
    return historical_service.get_by_code(code)

@app.get("/births", response_model=List[Birth])
async def get_births():
    return birth_service.get_all_data()

@app.get("/births/year/{year}", response_model=List[Birth])
async def get_births_by_year(year: int):
    return birth_service.get_by_year(year)

@app.get("/births/{code}", response_model=List[Birth])
async def get_births_by_code(code: str):
    return birth_service.get_by_code(code)

@app.get("/births/stats")
async def get_births_stats():
    return birth_service.get_stats()

@app.get("/births/filter", response_model=List[Birth])
async def get_filtered_births(geo: str = None, geo_object: str = None):
    print("Paramètres:", geo, geo_object)
    return birth_service.get_filtered_data(geo, geo_object)

@app.get("/geocodes/{code}")
async def get_geocode(code: str):
   return geocode_service.get_by_code(code)

@app.get("/geocodes/region/{reg}")
async def get_by_region(reg: str):
   return geocode_service.get_by_region(reg)

@app.get("/geocodes/department/{dep}")
async def get_by_department(dep: str):
   return geocode_service.get_by_department(dep)

@app.get("/geocodes/epci/{epci}/births")
async def get_epci_births(epci: str):
   return geocode_service.aggregate_births_by_epci(epci, birth_service)

@app.get("/geocodes/department/{dep}/births")
async def get_department_births(dep: str):
    return geocode_service.aggregate_births_by_department(dep, birth_service)

@app.get("/geocodes/region/{reg}/births")
async def get_region_births(reg: str):
   return geocode_service.aggregate_births_by_region(reg, birth_service)

@app.get("/geocodes/france/births")
async def get_france_births():
   return geocode_service.aggregate_births_france(birth_service)

@app.get("/revenues/median/commune/{code}")
async def get_commune_median_revenues(code: str):
    return revenue_service.get_median_revenues(code)

@app.get("/revenues/median/epci/{code}")
async def get_epci_median_revenues(code: str):
    return revenue_service.get_median_revenues_epci(code)

@app.get("/revenues/median/department/{code}")
async def get_department_median_revenues(code: str):
   return revenue_service.get_median_revenues_department(code)

@app.get("/revenues/median/region/{code}")
async def get_region_median_revenues(code: str):
   return revenue_service.get_median_revenues_region(code)

@app.get("/revenues/median/france")
async def get_france_median_revenues():
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
