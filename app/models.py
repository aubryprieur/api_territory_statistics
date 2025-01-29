from pydantic import BaseModel
from typing import Dict, Optional

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

class Revenue(BaseModel):
   commune: str
   median_revenues: dict

class RevenueEPCI(BaseModel):
   epci: str
   median_revenues: dict

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
