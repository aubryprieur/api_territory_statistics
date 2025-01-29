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
from .models import Population, HistoricalData, Birth, Revenue, Family, Childcare, LargeFamilyResponse


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

@app.get("/")
async def root():
    return {"message": "API Population 2021"}

@app.get("/population", response_model=List[Population])
async def get_population():
    return population_service.get_all_data()

@app.get("/population/{code}", response_model=List[Population])
async def get_population_by_code(code: str):
    data = population_service.get_by_code(code)
    if not data:
        raise HTTPException(status_code=404, detail="Code non trouvé")
    return data

@app.get("/population/children/commune/{code}")
async def get_commune_children(code: str):
    return population_service.get_children_under_3(code)

@app.get("/population/children/epci/{epci}")
async def get_epci_children(epci: str):
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@app.get("/population/children/department/{dep}")
async def get_department_children(dep: str):
    return population_service.aggregate_children_by_department(dep, geocode_service)

@app.get("/population/children/region/{reg}")
async def get_region_children(reg: str):
    return population_service.aggregate_children_by_region(reg, geocode_service)

@app.get("/population/children/france")
async def get_france_children():
    return population_service.aggregate_children_france(geocode_service)

@app.get("/population/rates/commune/{code}")
async def get_commune_rates(code: str):
    return population_service.get_population_and_children_rate(code)

@app.get("/population/rates/epci/{epci}")
async def get_epci_rates(epci: str):
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@app.get("/population/rates/department/{dep}")
async def get_department_rates(dep: str):
    return population_service.aggregate_children_by_department(dep, geocode_service)

@app.get("/population/rates/region/{reg}")
async def get_region_rates(reg: str):
    return population_service.aggregate_children_by_region(reg, geocode_service)

@app.get("/population/rates/france")
async def get_france_rates():
    return population_service.aggregate_children_france(geocode_service)

@app.get("/historical", response_model=List[HistoricalData])
async def get_historical():
    return historical_service.get_all_data()

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

@app.get("/families/france")
async def get_france_families(start_year: int = None, end_year: int = None):
    return family_service.get_families_france(start_year, end_year)
