from typing import List
from fastapi import FastAPI, HTTPException
from .services.population_service import PopulationService
from .services.historical_service import HistoricalService
from .models import Population, HistoricalData


app = FastAPI(title="API Population")
population_service = PopulationService()
historical_service = HistoricalService()

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

@app.get("/historical", response_model=List[HistoricalData])
async def get_historical():
    return historical_service.get_all_data()

@app.get("/historical/{code}", response_model=List[HistoricalData])
async def get_historical_by_code(code: str):
    return historical_service.get_by_code(code)
