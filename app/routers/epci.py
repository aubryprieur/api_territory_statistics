from fastapi import APIRouter, Depends, Request, Query
from typing import List, Dict
from app.security import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

# Importer vos schémas
from app.schemas import EPCICommunesChildcareResponse, CommuneChildcareRate
from app.schemas import EPCICommunesRevenueResponse, CommuneRevenueData
from app.schemas import EPCICommunesSchoolingResponse, CommuneSchoolingRate
from app.schemas import EPCICoupleWithChildrenResponse, CommuneFamilyData
from app.schemas import EPCISingleParentResponse, CommuneSingleParentData
from app.schemas import EPCILargeFamiliesResponse, CommuneLargeFamilyData
from app.schemas import EPCIFamilyEmploymentResponse, CommuneFamilyEmploymentData

# Importer vos services
from app.services.population_service import PopulationService
from app.services.geocode_service import GeoCodeService
from app.services.childcare_service import ChildcareService
from app.services.revenue_service import RevenueService
from app.services.schooling_service import SchoolingService
from app.services.family_service import FamilyService
from app.services.family_employment_service import FamilyEmploymentService

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

@router.get("/families/couples-with-children/{epci}",
    response_model=EPCICoupleWithChildrenResponse,
    summary="Obtenir les statistiques des couples avec enfants pour toutes les communes d'un EPCI",
    description="""Récupère les statistiques des couples avec enfants pour chaque commune appartenant à l'EPCI spécifié.

    Les données incluent pour chaque commune :
    - Le nombre total de ménages
    - Le nombre de couples avec enfants
    - Le pourcentage de couples avec enfants par rapport au total des ménages

    Ces données permettent d'analyser la structure familiale des communes d'un même territoire intercommunal.""",
    response_description="Liste des communes avec leurs statistiques de couples avec enfants, triée par pourcentage décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_couples_with_children(
    request: Request,
    epci: str
):
    """
    Récupère les statistiques des couples avec enfants pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    """
    # Création d'une instance du service
    service = FamilyService()
    return service.get_couples_with_children_by_epci(epci)

@router.get("/families/single-parent/{epci}",
    response_model=EPCISingleParentResponse,
    summary="Obtenir les statistiques des familles monoparentales pour toutes les communes d'un EPCI",
    description="""Récupère les statistiques des familles monoparentales pour chaque commune appartenant à l'EPCI spécifié.

    Les données incluent pour chaque commune :
    - Le nombre total de ménages
    - Le nombre de familles monoparentales
    - Le nombre de pères seuls
    - Le nombre de mères seules
    - Le pourcentage de familles monoparentales par rapport au total des ménages
    - Le pourcentage de pères seuls parmi les familles monoparentales
    - Le pourcentage de mères seules parmi les familles monoparentales

    Ces données permettent d'analyser la structure familiale des communes d'un même territoire intercommunal
    et d'identifier les zones avec une concentration plus élevée de familles monoparentales.""",
    response_description="Liste des communes avec leurs statistiques de familles monoparentales, triée par pourcentage décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_single_parent_families(
    request: Request,
    epci: str
):
    """
    Récupère les statistiques des familles monoparentales pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    """
    # Création d'une instance du service
    service = FamilyService()
    return service.get_single_parent_families_by_epci(epci)

@router.get("/families/large-families/{epci}",
    response_model=EPCILargeFamiliesResponse,
    summary="Obtenir les statistiques des familles nombreuses pour toutes les communes d'un EPCI",
    description="""Récupère les statistiques des familles nombreuses pour chaque commune appartenant à l'EPCI spécifié.

    Les données incluent pour chaque commune :
    - Le nombre total de ménages
    - Le nombre de familles nombreuses (3 enfants ou plus)
    - Le nombre de familles avec 3 enfants
    - Le nombre de familles avec 4 enfants ou plus
    - Le pourcentage de familles nombreuses par rapport au total des ménages
    - Le pourcentage de familles avec 3 enfants par rapport au total des ménages
    - Le pourcentage de familles avec 4 enfants ou plus par rapport au total des ménages

    Ces données permettent d'analyser la répartition des familles nombreuses sur un territoire intercommunal
    et d'identifier les zones nécessitant potentiellement plus d'infrastructures adaptées aux grandes familles.""",
    response_description="Liste des communes avec leurs statistiques de familles nombreuses, triée par pourcentage décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_large_families(
    request: Request,
    epci: str
):
    """
    Récupère les statistiques des familles nombreuses pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    """
    # Création d'une instance du service
    service = FamilyService()
    return service.get_large_families_by_epci(epci)

@router.get("/families/employment/under3/{epci}/communes",
    response_model=EPCIFamilyEmploymentResponse,
    summary="Obtenir les statistiques d'emploi des familles avec enfants de moins de 3 ans pour toutes les communes d'un EPCI",
    description="""Récupère la répartition des situations d'emploi des familles ayant des enfants de moins de 3 ans pour chaque commune de l'EPCI.

Les données incluent pour chaque commune :
- Le nombre total de familles avec enfants de moins de 3 ans
- Le nombre de couples avec les deux parents actifs ayant un emploi
- Le pourcentage de couples avec les deux parents actifs
- Le nombre de familles monoparentales avec le parent actif
- Le pourcentage de familles monoparentales avec le parent actif
- La distribution détaillée des différentes configurations familiales

Ces données permettent d'identifier les besoins en services de garde d'enfants et les disparités territoriales.""",
    response_description="Liste des communes avec leurs statistiques d'emploi des familles, triée par taux de double activité décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_communes_family_employment_under3(
    request: Request,
    epci: str,
    year: int = Query(None, description="Année des données (si non spécifiée, l'année la plus récente disponible est utilisée)")
):
    """
    Récupère les statistiques d'emploi des familles avec enfants de moins de 3 ans pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    - **year**: Année des données (optionnel)
    """
    # Création d'une instance du service
    service = FamilyEmploymentService()
    return service.get_communes_distribution_by_epci(epci, age_group="0", year=year)

@router.get("/families/employment/3to5/{epci}/communes",
    response_model=EPCIFamilyEmploymentResponse,
    summary="Obtenir les statistiques d'emploi des familles avec enfants de 3 à 5 ans pour toutes les communes d'un EPCI",
    description="""Récupère la répartition des situations d'emploi des familles ayant des enfants de 3 à 5 ans pour chaque commune de l'EPCI.

Les données incluent pour chaque commune :
- Le nombre total de familles avec enfants de 3 à 5 ans
- Le nombre de couples avec les deux parents actifs ayant un emploi
- Le pourcentage de couples avec les deux parents actifs
- Le nombre de familles monoparentales avec le parent actif
- Le pourcentage de familles monoparentales avec le parent actif
- La distribution détaillée des différentes configurations familiales

Ces statistiques sont particulièrement utiles pour l'analyse des besoins en services périscolaires.""",
    response_description="Liste des communes avec leurs statistiques d'emploi des familles, triée par taux de double activité décroissant")
@limiter.limit(DEFAULT_RATE)
async def get_epci_communes_family_employment_3to5(
    request: Request,
    epci: str,
    year: int = Query(None, description="Année des données (si non spécifiée, l'année la plus récente disponible est utilisée)")
):
    """
    Récupère les statistiques d'emploi des familles avec enfants de 3 à 5 ans pour chaque commune d'un EPCI :

    - **epci**: Code de l'EPCI
    - **year**: Année des données (optionnel)
    """
    # Création d'une instance du service
    service = FamilyEmploymentService()
    return service.get_communes_distribution_by_epci(epci, age_group="3", year=year)
