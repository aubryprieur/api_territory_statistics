"""
app/routers/iris.py
-------------------
Endpoints IRIS — Population multi-millésime
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Optional
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.iris_population_service import IrisPopulationService

router = APIRouter(
    prefix="/iris",
    tags=["IRIS"],
    dependencies=[Depends(get_current_user)],
)

limiter  = Limiter(key_func=get_remote_address)
iris_pop = IrisPopulationService()

DEFAULT_RATE   = "60/minute"
HIGH_LOAD_RATE = "30/minute"

_YEAR_QUERY = Query(
    None,
    description="Millésime (ex. 2022). Si absent, le dernier millésime disponible est utilisé.",
)


# ── 0. Millésimes disponibles ──────────────────────────────────────────────────
@router.get(
    "/population/years",
    summary="Millésimes disponibles",
    description="Retourne la liste des millésimes de population IRIS présents en base.",
)
@limiter.limit(DEFAULT_RATE)
async def get_available_years(request: Request):
    years = iris_pop.get_available_years()
    return {
        "available_years": years,
        "latest_year":     max(years) if years else None,
    }


# ── 1. Par code IRIS ───────────────────────────────────────────────────────────
@router.get(
    "/population/{iris_code}",
    summary="Population d'un IRIS",
    description=(
        "Retourne les données de population pour un IRIS précis "
        "(code à 9 caractères, ex. : 751010101). "
        "Sans paramètre `year`, le dernier millésime disponible est retourné."
    ),
)
@limiter.limit(DEFAULT_RATE)
async def get_iris_population(
    request: Request,
    iris_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_pop.get_by_iris(iris_code, year)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"IRIS {iris_code!r} introuvable pour le millésime demandé",
        )
    return result


# ── 2. Par commune ─────────────────────────────────────────────────────────────
@router.get(
    "/population/commune/{com_code}",
    summary="Population IRIS d'une commune",
    description=(
        "Retourne tous les IRIS d'une commune (code INSEE 5 chiffres) "
        "avec le total communal. Sans `year`, dernier millésime utilisé."
    ),
)
@limiter.limit(DEFAULT_RATE)
async def get_commune_iris_population(
    request: Request,
    com_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_pop.get_by_commune(com_code, year)
    if not result["iris_list"]:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun IRIS trouvé pour la commune {com_code!r} (millésime {result['year']})",
        )
    return result


# ── 3. Par EPCI ────────────────────────────────────────────────────────────────
@router.get(
    "/population/epci/{epci_code}",
    summary="Population IRIS d'un EPCI",
    description=(
        "Retourne tous les IRIS des communes membres d'un EPCI. "
        "Sans `year`, dernier millésime utilisé."
    ),
)
@limiter.limit(HIGH_LOAD_RATE)
async def get_epci_iris_population(
    request: Request,
    epci_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_pop.get_by_epci(epci_code, year)
    if not result["iris_list"]:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun IRIS trouvé pour l'EPCI {epci_code!r} (millésime {result['year']})",
        )
    return result


# ── 4. Par département ─────────────────────────────────────────────────────────
@router.get(
    "/population/department/{dep_code}",
    summary="Population IRIS d'un département",
    description=(
        "Retourne tous les IRIS d'un département. "
        "Sans `year`, dernier millésime utilisé."
    ),
)
@limiter.limit(HIGH_LOAD_RATE)
async def get_department_iris_population(
    request: Request,
    dep_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_pop.get_by_department(dep_code, year)
    if not result["iris_list"]:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun IRIS trouvé pour le département {dep_code!r} (millésime {result['year']})",
        )
    return result


# ── 5. Par région ──────────────────────────────────────────────────────────────
@router.get(
    "/population/region/{reg_code}",
    summary="Population IRIS d'une région",
    description=(
        "Retourne tous les IRIS d'une région. "
        "Sans `year`, dernier millésime utilisé."
    ),
)
@limiter.limit(HIGH_LOAD_RATE)
async def get_region_iris_population(
    request: Request,
    reg_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_pop.get_by_region(reg_code, year)
    if not result["iris_list"]:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun IRIS trouvé pour la région {reg_code!r} (millésime {result['year']})",
        )
    return result
