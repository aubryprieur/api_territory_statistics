from pydantic import BaseModel

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
