from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime

class BirthSchema(BaseModel):
    geo: str
    geo_object: str
    time_period: int
    obs_value: float

    class Config:
        orm_mode = True

class FamilySchema(BaseModel):
    geo_code: str
    year: int
    total_households: Optional[float] = None
    single_men: Optional[float] = None
    single_women: Optional[float] = None
    couples_with_children: Optional[float] = None
    single_parent_families: Optional[float] = None
    single_fathers: Optional[float] = None
    single_mothers: Optional[float] = None
    couples_without_children: Optional[float] = None
    large_families: Optional[float] = None
    children_under_24_no_sibling: Optional[float] = None
    children_under_24_one_sibling: Optional[float] = None
    children_under_24_two_siblings: Optional[float] = None
    children_under_24_three_siblings: Optional[float] = None
    children_under_24_four_or_more_siblings: Optional[float] = None

    class Config:
        orm_mode = True


class Population(BaseModel):
    NIVGEO: str
    CODGEO: str
    LIBGEO: str
    SEXE: int
    AGED100: int
    NB: float

class HistoricalData(BaseModel):
    CODGEO: str
    P21_POP: float
    P15_POP: float
    P10_POP: float
    D99_POP: float
    D90_POP: float
    D82_POP: float
    D75_POP: float
    D68_POP: float

class PopulationChildrenRate(BaseModel):
    total_population: float
    children_under_3: float
    children_3_to_5: float
    under_3_rate: float
    three_to_five_rate: float

class PopulationChildrenEPCI(BaseModel):
    epci: str
    epci_name: str
    total_population: float
    children_under_3: float
    children_3_to_5: float
    under_3_rate: float
    three_to_five_rate: float
    communes_count: int

class PopulationChildrenDepartment(BaseModel):
    department: str
    total_population: float
    children_under_3: float
    children_3_to_5: float
    under_3_rate: float
    three_to_five_rate: float
    communes_count: int

class PopulationChildrenRegion(BaseModel):
    region: str
    total_population: float
    children_under_3: float
    children_3_to_5: float
    under_3_rate: float
    three_to_five_rate: float
    communes_count: int
    departments_count: int

class PopulationChildrenFrance(BaseModel):
    total_population: float
    children_under_3: float
    children_3_to_5: float
    under_3_rate: float
    three_to_five_rate: float
    communes_count: int
    departments_count: int
    regions_count: int

class GeoCode(BaseModel):
    CODE: str
    LIBELLE: str
    TYPE: str
    REG: str
    DEP: str

class RevenueData(BaseModel):
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class Revenue(BaseModel):
    commune: str
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class RevenueEPCI(BaseModel):
    epci: str
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class RevenueDepartment(BaseModel):
    department: str
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class RevenueRegion(BaseModel):
    region: str
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class RevenueFrance(BaseModel):
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class Childcare(BaseModel):
    coverage_rates: Dict[str, float]
    evolution: Optional[Dict] = None
    commune_name: Optional[str] = None
    epci: Optional[Dict] = None
    department: Optional[Dict] = None
    region: Optional[Dict] = None

class LargeFamilyData(BaseModel):
    total_families: float
    families_with_3_children: float
    families_with_4_plus_children: float
    total_large_families: float
    large_families_percentage: float

class LargeFamilyResponse(BaseModel):
    commune: Optional[str] = None
    epci: Optional[str] = None
    department: Optional[str] = None
    region: Optional[str] = None
    large_families_data: Dict[int, LargeFamilyData]

from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime

class PublicSafetyBase(BaseModel):
    territory_type: str
    territory_code: str
    year: int
    indicator_class: str
    rate: float

class PublicSafetyCreate(PublicSafetyBase):
    pass

class PublicSafety(PublicSafetyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class PublicSafetyDataItem(BaseModel):
    year: int
    indicator_class: str
    rate: float

class GeoLevelData(BaseModel):
    code: str
    name: Optional[str]
    data: List[PublicSafetyDataItem]

class PublicSafetyResponse(BaseModel):
    commune: GeoLevelData
    department: GeoLevelData
    region: GeoLevelData

class EmploymentRates(BaseModel):
    activity_rate: float
    employment_rate: float
    part_time_rate_25_54: float
    part_time_rate_15_64: float

class EmploymentResponse(BaseModel):
    territory_type: str
    code: str
    name: str
    rates: EmploymentRates

class SchoolingData(BaseModel):
    # Pour les 2 ans
    total_children_2y: float
    schooled_children_2y: float
    schooling_rate_2y: float
    # Pour les 3-5 ans
    total_children_3_5y: float
    schooled_children_3_5y: float
    schooling_rate_3_5y: float

class SchoolingResponse(BaseModel):
    territory_type: str
    code: str
    name: str
    data: Dict[int, SchoolingData]

class FamilyTypeDistribution(BaseModel):
    code: str
    count: float
    percentage: float

class FamilyEmploymentDistribution(BaseModel):
    total_count: float
    distributions: Dict[str, FamilyTypeDistribution]
    age_group: str

class FamilyEmploymentResponse(BaseModel):
    territory_type: str
    code: str
    name: str
    data: Dict[int, FamilyEmploymentDistribution]

class CommuneChildcareRate(BaseModel):
    code: str
    name: str
    global_coverage_rate: float

class EPCICommunesChildcareResponse(BaseModel):
    epci: str
    epci_name: str
    year: int
    average_coverage_rate: float
    communes_count: int
    communes: List[CommuneChildcareRate]

class CommuneRevenueData(BaseModel):
    code: str
    name: str
    median_revenues: Dict[int, Optional[float]]
    poverty_rates: Dict[int, Optional[float]]

class EPCICommunesRevenueResponse(BaseModel):
    epci: str
    epci_name: str
    communes_count: int
    latest_year: Optional[int] = None
    communes: List[CommuneRevenueData]

class CommuneSchoolingRate(BaseModel):
    code: str
    name: str
    # Données pour les enfants de 2 ans
    schooling_rate_2y: float
    total_children_2y: float
    schooled_children_2y: float
    # Données pour les enfants de 3 à 5 ans
    schooling_rate_3_5y: float
    total_children_3_5y: float
    schooled_children_3_5y: float

class EPCICommunesSchoolingResponse(BaseModel):
    epci: str
    epci_name: str
    year: int
    communes_count: int
    average_schooling_rate_2y: float
    average_schooling_rate_3_5y: float
    communes: List[CommuneSchoolingRate]

class CommuneFamilyData(BaseModel):
    code: str
    name: str
    total_households: float
    couples_with_children: float
    couples_with_children_percentage: float

class EPCICoupleWithChildrenResponse(BaseModel):
    epci: str
    epci_name: str
    year: int
    communes_count: int
    total_households: float
    total_couples_with_children: float
    epci_couples_with_children_percentage: float
    communes: List[CommuneFamilyData]

class CommuneSingleParentData(BaseModel):
    code: str
    name: str
    total_households: float
    single_parent_families: float
    single_fathers: float
    single_mothers: float
    single_parent_percentage: float
    single_father_percentage: float  # Ajout du pourcentage de pères seuls
    single_mother_percentage: float

class EPCISingleParentResponse(BaseModel):
    epci: str
    epci_name: str
    year: int
    communes_count: int
    total_households: float
    total_single_parent_families: float
    total_single_fathers: float
    total_single_mothers: float
    epci_single_parent_percentage: float
    epci_single_father_percentage: float  # Ajout du pourcentage de pères seuls au niveau EPCI
    epci_single_mother_percentage: float
    communes: List[CommuneSingleParentData]

class CommuneLargeFamilyData(BaseModel):
    code: str
    name: str
    total_households: float
    large_families: float
    families_3_children: float
    families_4_plus_children: float
    large_families_percentage: float
    families_3_children_percentage: float
    families_4_plus_percentage: float

class EPCILargeFamiliesResponse(BaseModel):
    epci: str
    epci_name: str
    year: int
    communes_count: int
    total_households: float
    total_large_families: float
    total_families_3_children: float
    total_families_4_plus_children: float
    epci_large_families_percentage: float
    epci_families_3_children_percentage: float
    epci_families_4_plus_percentage: float
    communes: List[CommuneLargeFamilyData]

class CommuneFamilyEmploymentData(BaseModel):
    code: str
    name: str
    total_families: float
    dual_active_count: float
    dual_active_rate: float
    single_parent_active_count: float
    single_parent_active_rate: float
    distributions: Dict[str, FamilyTypeDistribution]

class EPCIFamilyEmploymentResponse(BaseModel):
    epci: str
    epci_name: str
    year: int
    age_group: str
    communes_count: int
    total_families: float
    total_dual_active: float
    total_single_parent_active: float
    epci_dual_active_rate: float
    epci_single_parent_active_rate: float
    communes: List[CommuneFamilyEmploymentData]

class CommuneEmploymentRates(BaseModel):
    code: str
    name: str
    women_15_64: float
    women_active_15_64: float
    women_employed_15_64: float
    activity_rate: float
    employment_rate: float
    part_time_rate_25_54: float
    part_time_rate_15_64: float

class EPCICommunesEmploymentResponse(BaseModel):
    epci: str
    epci_name: str
    communes_count: int
    epci_activity_rate: float
    epci_employment_rate: float
    epci_part_time_rate_25_54: float
    epci_part_time_rate_15_64: float
    communes: List[CommuneEmploymentRates]

class YearlyViolenceData(BaseModel):
    year: int
    rate: float

class CommuneDomesticViolenceData(BaseModel):
    code: str
    name: str
    population: float
    average_rate: float
    yearly_data: List[YearlyViolenceData]

class EPCIDomesticViolenceResponse(BaseModel):
    epci: str
    epci_name: str
    communes_count: int
    total_population: float
    epci_average_rate: float
    communes: List[CommuneDomesticViolenceData]
