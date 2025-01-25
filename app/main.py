from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from .services.population_service import PopulationService
from .services.historical_service import HistoricalService
from .services.birth_service import BirthService
from .services.geocode_service import GeoCodeService
from .services.revenue_service import RevenueService
from .models import Population, HistoricalData, Birth, Revenue

app = FastAPI(title="API Population")
app.mount("/static", StaticFiles(directory="static"), name="static")
population_service = PopulationService()
historical_service = HistoricalService()
birth_service = BirthService()
geocode_service = GeoCodeService()
revenue_service = RevenueService()

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
   return revenue_service.get_iris_revenues_by_commune(commune)
