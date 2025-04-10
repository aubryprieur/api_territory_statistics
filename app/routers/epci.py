from fastapi import APIRouter, Depends, Request, Query
from typing import List, Dict
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.schemas import EPCICommunesChildcareResponse, CommuneChildcareRate
from app.schemas import EPCICommunesRevenueResponse, CommuneRevenueData
from app.schemas import EPCICommunesSchoolingResponse, CommuneSchoolingRate

# Importer vos services
from app.services.population_service import PopulationService
from app.services.geocode_service import GeoCodeService
from app.services.childcare_service import ChildcareService
from app.services.revenue_service import RevenueService
from app.services.schooling_service import SchoolingService

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

@router.get("/childcare/{epci}/communes",
    summary="Obtenir les taux de couverture globale des modes d'accueil pour toutes les communes d'un EPCI",
    description="Récupère les taux de couverture globale des différents modes d'accueil pour chaque commune appartenant à l'EPCI spécifié. Ces données permettent de comparer les niveaux d'accès aux services de garde d'enfants entre les communes d'un même territoire intercommunal.",
    response_description="Liste des communes avec leurs taux de couverture, triée par taux décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_communes_childcare(
    request: Request,
    epci: str,
    year: int = Query(None, description="Année des données (si non spécifiée, l'année la plus récente disponible est utilisée)")
):
    """
    Récupère les taux de couverture pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    - **year**: Année des données (optionnel)
    """
    # Création d'une instance du service
    service = ChildcareService()
    return service.get_communes_coverage_by_epci(epci, year)

@router.get("/revenues/{epci}/communes",
    summary="Obtenir les revenus médians et taux de pauvreté pour toutes les communes d'un EPCI",
    description="Récupère les revenus médians et taux de pauvreté pour chaque commune appartenant à l'EPCI spécifié. Ces données permettent de comparer les niveaux de revenus entre les communes d'un même territoire intercommunal.",
    response_description="Liste des communes avec leurs revenus médians et taux de pauvreté, triée par revenu médian décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_communes_revenues(
    request: Request,
    epci: str
):
    """
    Récupère les données de revenus pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    """
    # Création d'une instance du service
    service = RevenueService()
    return service.get_communes_revenues_by_epci(epci)

@router.get("/education/schooling/{epci}/communes",
    response_model=EPCICommunesSchoolingResponse,
    summary="Obtenir les taux de scolarisation des enfants de 2 ans et de 3 à 5 ans pour toutes les communes d'un EPCI",
    description="""Récupère les taux de scolarisation des enfants de 2 ans et de 3 à 5 ans pour chaque commune appartenant à l'EPCI spécifié.""",
    response_description="Liste des communes avec leurs taux de scolarisation par tranche d'âge")
@limiter.limit(DEFAULT_RATE)
async def get_epci_communes_schooling(
    request: Request,
    epci: str,
    sort_by: str = Query("2y", description="Critère de tri ('2y' pour trier par taux à 2 ans, '3_5y' pour trier par taux à 3-5 ans)")
):
    """
    Récupère les taux de scolarisation des enfants par tranche d'âge pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    - **sort_by**: Critère de tri ('2y' ou '3_5y')
    """
    # Création d'une instance du service
    service = SchoolingService()
    data = service.get_communes_schooling_by_epci(epci)

    # Trier selon le critère choisi
    if sort_by == "3_5y" and "communes" in data:
        data["communes"].sort(key=lambda x: x["schooling_rate_3_5y"], reverse=True)

    return data
