from fastapi import APIRouter
from app.routers import epci
# Ajoutez d'autres routeurs au fur et à mesure

api_router = APIRouter()
api_router.include_router(epci.router)
# include_router pour d'autres routeurs
