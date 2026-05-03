"""
app/routers/iris_education.py
-------------------------------
Endpoints IRIS — Diplômes et formation (millésime 2022+)
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Optional
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.iris_education_service import IrisEducationService

router = APIRouter(
    prefix="/iris",
    tags=["IRIS - Diplômes et formation"],
    dependencies=[Depends(get_current_user)],
)

limiter          = Limiter(key_func=get_remote_address)
iris_edu_svc     = IrisEducationService()

DEFAULT_RATE   = "60/minute"
HIGH_LOAD_RATE = "30/minute"

_YEAR_QUERY = Query(
    None,
    description="Millésime (ex. 2022). Si absent, le dernier millésime disponible est utilisé.",
)


@router.get("/education/years", summary="Millésimes disponibles — Diplômes et formation")
@limiter.limit(DEFAULT_RATE)
async def get_education_years(request: Request):
    years = iris_edu_svc.get_available_years()
    return {"available_years": years, "latest_year": max(years) if years else None}


@router.get("/education/{iris_code}", summary="Diplômes et formation d'un IRIS")
@limiter.limit(DEFAULT_RATE)
async def get_iris_education(
    request: Request,
    iris_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_edu_svc.get_by_iris(iris_code, year)
    if not result:
        raise HTTPException(status_code=404, detail=f"IRIS {iris_code!r} introuvable")
    return result


@router.get("/education/commune/{com_code}", summary="Diplômes et formation IRIS d'une commune")
@limiter.limit(DEFAULT_RATE)
async def get_commune_iris_education(
    request: Request,
    com_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_edu_svc.get_by_commune(com_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la commune {com_code!r}")
    return result


@router.get("/education/epci/{epci_code}", summary="Diplômes et formation IRIS d'un EPCI")
@limiter.limit(HIGH_LOAD_RATE)
async def get_epci_iris_education(
    request: Request,
    epci_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_edu_svc.get_by_epci(epci_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour l'EPCI {epci_code!r}")
    return result


@router.get("/education/department/{dep_code}", summary="Diplômes et formation IRIS d'un département")
@limiter.limit(HIGH_LOAD_RATE)
async def get_department_iris_education(
    request: Request,
    dep_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_edu_svc.get_by_department(dep_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour le département {dep_code!r}")
    return result


@router.get("/education/region/{reg_code}", summary="Diplômes et formation IRIS d'une région")
@limiter.limit(HIGH_LOAD_RATE)
async def get_region_iris_education(
    request: Request,
    reg_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_edu_svc.get_by_region(reg_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la région {reg_code!r}")
    return result
