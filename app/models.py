from pydantic import BaseModel
from typing import Dict, Optional, List

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

class Birth(BaseModel):
   GEO: str
   GEO_OBJECT: str
   FREQ: str
   EC_MEASURE: str
   TIME_PERIOD: int
   OBS_VALUE: float

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

class Family(BaseModel):
    commune: str
    family_data: dict
    evolution: dict

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
