"""
app/routers/iris_map.py
-----------------------
Cartes IRIS : contours simplifiés et indicateurs par IRIS d'une commune (2017, 2022).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.security import get_current_user
from app.services.iris_map_service import IrisMapService

router = APIRouter(prefix="/iris", tags=["IRIS - Cartes"], dependencies=[Depends(get_current_user)])
limiter = Limiter(key_func=get_remote_address)
svc = IrisMapService()


@router.get("/map/indicators", summary="Indicateurs disponibles pour les cartes IRIS")
@limiter.limit("60/minute")
async def get_map_indicators(request: Request):
    return svc.indicators()


@router.get("/geometry/commune/{com_code}", summary="Contours des IRIS d'une commune (GeoJSON simplifié, WGS84)")
@limiter.limit("60/minute")
async def get_commune_iris_geometry(request: Request, com_code: str):
    features = svc.geometries(com_code.zfill(5))
    if not features:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS pour la commune {com_code!r}")
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": f.pop("geometry"), "properties": f} for f in features]}


@router.get("/map/commune/{com_code}", summary="Carte IRIS d'une commune pour un indicateur",
            description="Contours des IRIS, valeur, effectif et total par IRIS et par millésime, valeur de la commune "
                        "(somme des IRIS). Paramètre `indicator` : voir /iris/map/indicators.")
@limiter.limit("60/minute")
async def get_commune_iris_map(request: Request, com_code: str, indicator: str):
    result = svc.commune_map(com_code.zfill(5), indicator)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS pour la commune {com_code!r}")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
