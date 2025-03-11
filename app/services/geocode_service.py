from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import GeoCode

class GeoCodeService:
    def __init__(self):
        self.db = SessionLocal()

    def get_by_code(self, code: str):
        """Récupère les géocodes pour un code spécifique"""
        return [record.__dict__ for record in self.db.query(GeoCode).filter(GeoCode.codgeo == code).all()]

    def get_by_region(self, reg: str):
        """Récupère les géocodes pour une région spécifique"""
        return [record.__dict__ for record in self.db.query(GeoCode).filter(GeoCode.reg == reg).all()]

    def get_by_department(self, dep: str):
        """Récupère les géocodes pour un département spécifique"""
        return [record.__dict__ for record in self.db.query(GeoCode).filter(GeoCode.dep == dep).all()]

    def aggregate_births_by_epci(self, epci: str, birth_service):
        """Agrège les naissances par EPCI"""
        communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == epci).all()
        communes = [c[0] for c in communes]

        if not communes:
            return {"error": "EPCI non trouvé"}

        epci_name = self.db.query(GeoCode.libepci).filter(GeoCode.epci == epci).first()

        births_data = []
        for commune in communes:
            births_data.extend(birth_service.get_by_code(commune))

        yearly_births = {}
        for birth in births_data:
            year = birth.time_period
            if year not in yearly_births:
                yearly_births[year] = 0
            yearly_births[year] += birth.obs_value

        return {
            "epci": epci,
            "epci_name": epci_name[0] if epci_name else "",
            "total_births": float(sum(birth.obs_value for birth in births_data)),
            "communes_count": int(len(communes)),
            "births_by_year": {int(k): float(v) for k, v in yearly_births.items()}
        }
