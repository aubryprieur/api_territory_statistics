"""
app/routers/iris_housing.py
-----------------------------
Endpoints IRIS — Logement (millésime 2022+)
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Optional
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.iris_housing_service import IrisHousingService

router = APIRouter(
    prefix="/iris",
    tags=["IRIS - Logement"],
    dependencies=[Depends(get_current_user)],
)

limiter         = Limiter(key_func=get_remote_address)
iris_housing_svc = IrisHousingService()

DEFAULT_RATE   = "60/minute"
HIGH_LOAD_RATE = "30/minute"

_YEAR_QUERY = Query(
    None,
    description="Millésime (ex. 2022). Si absent, le dernier millésime disponible est utilisé.",
)


@router.get("/housing/years", summary="Millésimes disponibles — Logement")
@limiter.limit(DEFAULT_RATE)
async def get_housing_years(request: Request):
    years = iris_housing_svc.get_available_years()
    return {"available_years": years, "latest_year": max(years) if years else None}


@router.get("/housing/{iris_code}", summary="Logement d'un IRIS")
@limiter.limit(DEFAULT_RATE)
async def get_iris_housing(
    request: Request,
    iris_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_housing_svc.get_by_iris(iris_code, year)
    if not result:
        raise HTTPException(status_code=404, detail=f"IRIS {iris_code!r} introuvable")
    return result


@router.get("/housing/commune/{com_code}", summary="Logement IRIS d'une commune")
@limiter.limit(DEFAULT_RATE)
async def get_commune_iris_housing(
    request: Request,
    com_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_housing_svc.get_by_commune(com_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la commune {com_code!r}")
    return result


@router.get("/housing/epci/{epci_code}", summary="Logement IRIS d'un EPCI")
@limiter.limit(HIGH_LOAD_RATE)
async def get_epci_iris_housing(
    request: Request,
    epci_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_housing_svc.get_by_epci(epci_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour l'EPCI {epci_code!r}")
    return result


@router.get("/housing/department/{dep_code}", summary="Logement IRIS d'un département")
@limiter.limit(HIGH_LOAD_RATE)
async def get_department_iris_housing(
    request: Request,
    dep_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_housing_svc.get_by_department(dep_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour le département {dep_code!r}")
    return result


@router.get("/housing/region/{reg_code}", summary="Logement IRIS d'une région")
@limiter.limit(HIGH_LOAD_RATE)
async def get_region_iris_housing(
    request: Request,
    reg_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_housing_svc.get_by_region(reg_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la région {reg_code!r}")
    return result
