"""
app/routers/iris_activity.py
------------------------------
Endpoints IRIS — Activité des résidents (millésime 2022+)
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Optional
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.iris_activity_service import IrisActivityService

router = APIRouter(
    prefix="/iris",
    tags=["IRIS - Activité"],
    dependencies=[Depends(get_current_user)],
)

limiter          = Limiter(key_func=get_remote_address)
iris_activity_svc = IrisActivityService()

DEFAULT_RATE   = "60/minute"
HIGH_LOAD_RATE = "30/minute"

_YEAR_QUERY = Query(
    None,
    description="Millésime (ex. 2022). Si absent, le dernier millésime disponible est utilisé.",
)


@router.get("/activity/years", summary="Millésimes disponibles — Activité")
@limiter.limit(DEFAULT_RATE)
async def get_activity_years(request: Request):
    years = iris_activity_svc.get_available_years()
    return {"available_years": years, "latest_year": max(years) if years else None}


@router.get("/activity/{iris_code}", summary="Activité d'un IRIS")
@limiter.limit(DEFAULT_RATE)
async def get_iris_activity(
    request: Request, iris_code: str, year: Optional[int] = _YEAR_QUERY,
):
    result = iris_activity_svc.get_by_iris(iris_code, year)
    if not result:
        raise HTTPException(status_code=404, detail=f"IRIS {iris_code!r} introuvable")
    return result


@router.get("/activity/commune/{com_code}", summary="Activité IRIS d'une commune")
@limiter.limit(DEFAULT_RATE)
async def get_commune_iris_activity(
    request: Request, com_code: str, year: Optional[int] = _YEAR_QUERY,
):
    result = iris_activity_svc.get_by_commune(com_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la commune {com_code!r}")
    return result


@router.get("/activity/epci/{epci_code}", summary="Activité IRIS d'un EPCI")
@limiter.limit(HIGH_LOAD_RATE)
async def get_epci_iris_activity(
    request: Request, epci_code: str, year: Optional[int] = _YEAR_QUERY,
):
    result = iris_activity_svc.get_by_epci(epci_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour l'EPCI {epci_code!r}")
    return result


@router.get("/activity/department/{dep_code}", summary="Activité IRIS d'un département")
@limiter.limit(HIGH_LOAD_RATE)
async def get_department_iris_activity(
    request: Request, dep_code: str, year: Optional[int] = _YEAR_QUERY,
):
    result = iris_activity_svc.get_by_department(dep_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour le département {dep_code!r}")
    return result


@router.get("/activity/region/{reg_code}", summary="Activité IRIS d'une région")
@limiter.limit(HIGH_LOAD_RATE)
async def get_region_iris_activity(
    request: Request, reg_code: str, year: Optional[int] = _YEAR_QUERY,
):
    result = iris_activity_svc.get_by_region(reg_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la région {reg_code!r}")
    return result
