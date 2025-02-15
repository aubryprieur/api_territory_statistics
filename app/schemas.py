from pydantic import BaseModel
from typing import Dict, Optional, List


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

class IrisRevenueData(BaseModel):
    iris_code: str
    iris_name: str
    median: float
    poverty_rate: float

class IrisRevenueResponse(BaseModel):
    commune: str
    iris_count: int
    iris_data: Dict[int, List[IrisRevenueData]]

class IrisData(BaseModel):
    iris_code: str
    iris_name: str
    data: dict

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

class PublicSafetyDataItem(BaseModel):
    annee: int
    classe: str
    tauxpourmille: float

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
