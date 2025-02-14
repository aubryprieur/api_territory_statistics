from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Birth  # Utilise le modèle SQLAlchemy

class BirthService:
    def __init__(self):
        self.db = SessionLocal()

    def get_by_code(self, geo: str):
        """
        Récupère les données de naissance pour une commune spécifique depuis PostgreSQL.
        """
        return self.db.query(Birth).filter(Birth.geo == geo).order_by(Birth.time_period).all()

    def get_by_type(self, geo_object: str):
        """
        Récupère les données de naissance pour un type de territoire donné (ex: COM, DEP, REG).
        """
        return self.db.query(Birth).filter(Birth.geo_object == geo_object).all()

    def get_births_trend(self, geo: str):
        """
        Agrège les naissances par année pour une commune.
        """
        results = (
            self.db.query(Birth.time_period, Birth.obs_value)
            .filter(Birth.geo == geo)
            .order_by(Birth.time_period)
            .all()
        )
        return {year: births for year, births in results}
