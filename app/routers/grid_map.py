"""
app/routers/grid_map.py
-----------------------
Cartes carroyées (Insee, Filosofi 2021, carreaux de 1 km) : carreaux habités touchant une commune.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.security import get_current_user
from app.services.grid_map_service import GridMapService

router = APIRouter(prefix="/grid", tags=["Carreaux - Cartes"], dependencies=[Depends(get_current_user)])
limiter = Limiter(key_func=get_remote_address)
svc = GridMapService()


@router.get("/map/indicators", summary="Indicateurs disponibles pour les cartes carroyées")
@limiter.limit("60/minute")
async def get_grid_indicators(request: Request):
    return svc.indicators()


@router.get("/map/commune/{com_code}", summary="Carreaux de 1 km d'une commune pour un indicateur (Filosofi 2021)")
@limiter.limit("60/minute")
async def get_commune_grid_map(request: Request, com_code: str, indicator: str):
    result = svc.commune_map(com_code, indicator)
    if result.get("error", "").startswith("Indicateur inconnu"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result
