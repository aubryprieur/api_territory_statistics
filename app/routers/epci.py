from fastapi import APIRouter, Depends, Request
from typing import List, Dict
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

# Importer vos services
from app.services.population_service import PopulationService
from app.services.geocode_service import GeoCodeService
# Importer d'autres services selon vos besoins

# Créer un routeur
router = APIRouter(
    prefix="/epci",
    tags=["EPCI"],
    dependencies=[Depends(get_current_user)]
)

# Créer des instances de vos services
population_service = PopulationService()
geocode_service = GeoCodeService()

# Définir les limites de taux
DEFAULT_RATE = "60/minute"

# Créer une instance du limiter
limiter = Limiter(key_func=get_remote_address)

@router.get("/population/children/{epci}",
    summary="Obtenir les données des enfants de 0-5 ans pour un EPCI",
    description="Agrège les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour toutes les communes d'un EPCI",
    response_description="Les données démographiques incluant la population totale de l'EPCI, le nombre d'enfants par tranche d'âge, leurs taux et le nombre de communes")
@limiter.limit(DEFAULT_RATE)
async def get_epci_children(request: Request, epci: str):
    """
    Agrège les statistiques des enfants pour un EPCI :

    - **epci**: Code de l'EPCI
    """
    return population_service.aggregate_children_by_epci(epci, geocode_service)

@router.get("/population/children/{epci}/communes",
    summary="Obtenir les données des enfants de 0-5 ans pour toutes les communes d'un EPCI",
    description="Récupère les statistiques sur les enfants de moins de 3 ans et de 3 à 5 ans pour chaque commune appartenant à l'EPCI spécifié",
    response_description="Liste des données démographiques par commune incluant la population totale, le nombre d'enfants par tranche d'âge et leurs taux")
@limiter.limit(DEFAULT_RATE)
async def get_epci_communes_children(request: Request, epci: str):
    """
    Récupère les statistiques des enfants pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    """
    return population_service.get_children_by_epci_communes(epci, geocode_service)

# Vous pouvez ajouter d'autres endpoints EPCI ici
