from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import SessionLocal
from app.models import Historical

class HistoricalService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def _format_historical_data(self, data: List[Historical]) -> List[dict]:
        """Convertit les données du modèle au format attendu par l'API"""
        result = []
        for item in data:
            result.append({
                "CODGEO": item.codgeo,
                "D68_POP": item.pop_1968 or 0.0,
                "D75_POP": item.pop_1975 or 0.0,
                "D82_POP": item.pop_1982 or 0.0,
                "D90_POP": item.pop_1990 or 0.0,
                "D99_POP": item.pop_1999 or 0.0,
                "P10_POP": item.pop_2010 or 0.0,
                "P15_POP": item.pop_2015 or 0.0,
                "P21_POP": item.pop_2021 or 0.0
            })
        return result

    def get_all_data(self) -> List[dict]:
        """Récupère toutes les données historiques"""
        try:
            data = self.db.query(Historical).all()
            return self._format_historical_data(data)
        except Exception as e:
            print(f"Erreur dans get_all_data: {str(e)}")
            return []
        finally:
            self.close()

    def get_by_code(self, codgeo: str) -> List[dict]:
        """Récupère les données historiques pour une commune spécifique"""
        try:
            data = self.db.query(Historical).filter(Historical.codgeo == str(codgeo)).all()
            return self._format_historical_data(data)
        except Exception as e:
            print(f"Erreur dans get_by_code: {str(e)}")
            return []
        finally:
            self.close()
