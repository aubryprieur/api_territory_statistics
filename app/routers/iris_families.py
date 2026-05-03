"""
app/routers/iris_families.py
-----------------------------
Endpoints IRIS — Couples, familles, ménages (millésime 2022+)
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Optional
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.iris_families_service import IrisFamiliesService

router = APIRouter(
    prefix="/iris",
    tags=["IRIS - Familles"],
    dependencies=[Depends(get_current_user)],
)

limiter      = Limiter(key_func=get_remote_address)
iris_fam_svc = IrisFamiliesService()

DEFAULT_RATE   = "60/minute"
HIGH_LOAD_RATE = "30/minute"

_YEAR_QUERY = Query(
    None,
    description="Millésime (ex. 2022). Si absent, le dernier millésime disponible est utilisé.",
)


# ── 0. Millésimes disponibles ──────────────────────────────────────────────────
@router.get(
    "/families/years",
    summary="Millésimes disponibles — Familles",
    description="Retourne la liste des millésimes disponibles pour les données familles/ménages.",
)
@limiter.limit(DEFAULT_RATE)
async def get_families_years(request: Request):
    years = iris_fam_svc.get_available_years()
    return {"available_years": years, "latest_year": max(years) if years else None}


# ── 1. Par code IRIS ───────────────────────────────────────────────────────────
@router.get(
    "/families/{iris_code}",
    summary="Familles/ménages d'un IRIS",
    description="Retourne les données couples-familles-ménages pour un IRIS précis (9 caractères).",
)
@limiter.limit(DEFAULT_RATE)
async def get_iris_families(
    request: Request,
    iris_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_fam_svc.get_by_iris(iris_code, year)
    if not result:
        raise HTTPException(status_code=404, detail=f"IRIS {iris_code!r} introuvable")
    return result


# ── 2. Par commune ─────────────────────────────────────────────────────────────
@router.get(
    "/families/commune/{com_code}",
    summary="Familles/ménages IRIS d'une commune",
    description="Retourne tous les IRIS d'une commune avec leurs données familles/ménages.",
)
@limiter.limit(DEFAULT_RATE)
async def get_commune_iris_families(
    request: Request,
    com_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_fam_svc.get_by_commune(com_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la commune {com_code!r}")
    return result


# ── 3. Par EPCI ────────────────────────────────────────────────────────────────
@router.get(
    "/families/epci/{epci_code}",
    summary="Familles/ménages IRIS d'un EPCI",
    description="Retourne tous les IRIS des communes membres d'un EPCI avec leurs données familles/ménages.",
)
@limiter.limit(HIGH_LOAD_RATE)
async def get_epci_iris_families(
    request: Request,
    epci_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_fam_svc.get_by_epci(epci_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour l'EPCI {epci_code!r}")
    return result


# ── 4. Par département ─────────────────────────────────────────────────────────
@router.get(
    "/families/department/{dep_code}",
    summary="Familles/ménages IRIS d'un département",
    description="Retourne tous les IRIS d'un département avec leurs données familles/ménages.",
)
@limiter.limit(HIGH_LOAD_RATE)
async def get_department_iris_families(
    request: Request,
    dep_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_fam_svc.get_by_department(dep_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour le département {dep_code!r}")
    return result


# ── 5. Par région ──────────────────────────────────────────────────────────────
@router.get(
    "/families/region/{reg_code}",
    summary="Familles/ménages IRIS d'une région",
    description="Retourne tous les IRIS d'une région avec leurs données familles/ménages.",
)
@limiter.limit(HIGH_LOAD_RATE)
async def get_region_iris_families(
    request: Request,
    reg_code: str,
    year: Optional[int] = _YEAR_QUERY,
):
    result = iris_fam_svc.get_by_region(reg_code, year)
    if not result["iris_list"]:
        raise HTTPException(status_code=404, detail=f"Aucun IRIS trouvé pour la région {reg_code!r}")
    return result
