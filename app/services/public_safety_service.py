from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Optional
from app.database import SessionLocal
from app.models import PublicSafety, GeoCode

class PublicSafetyService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def _format_safety_data(self, data) -> list:
        """Formate les données de sécurité pour l'API"""
        return [
            {
                "year": item.year,
                "indicator_class": item.indicator_class,
                "rate": float(item.rate)
            }
            for item in data
        ]

    def get_by_commune(self, code: str) -> Dict:
        """Récupère les données de sécurité pour une commune et ses territoires parents"""
        try:
            # Récupérer les informations géographiques
            geo_info = self.db.query(GeoCode).filter(GeoCode.codgeo == str(code)).first()

            if not geo_info:
                return {
                    "commune": {"code": code, "name": None, "data": []},
                    "department": {"code": "", "name": None, "data": []},
                    "region": {"code": "", "name": None, "data": []}
                }

            # Récupérer les données pour chaque niveau
            commune_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'commune',
                    PublicSafety.territory_code == str(code)
                )
            ).all()

            department_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'department',
                    PublicSafety.territory_code == str(geo_info.dep)
                )
            ).all()

            region_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'region',
                    PublicSafety.territory_code == str(geo_info.reg)
                )
            ).all()

            return {
                "commune": {
                    "code": code,
                    "name": geo_info.libgeo,
                    "data": self._format_safety_data(commune_data)
                },
                "department": {
                    "code": geo_info.dep,
                    "name": f"Département {geo_info.dep}",
                    "data": self._format_safety_data(department_data)
                },
                "region": {
                    "code": geo_info.reg,
                    "name": f"Région {geo_info.reg}",
                    "data": self._format_safety_data(region_data)
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_commune: {str(e)}")
            return {
                "commune": {"code": code, "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {"code": "", "name": None, "data": []}
            }
        finally:
            self.close()

    def get_by_department(self, dep: str) -> Dict:
        """Récupère les données de sécurité pour un département et sa région parente"""
        try:
            # Récupérer les informations géographiques
            geo_info = self.db.query(GeoCode).filter(GeoCode.dep == str(dep)).first()

            if not geo_info:
                return {
                    "commune": {"code": "", "name": None, "data": []},
                    "department": {"code": dep, "name": None, "data": []},
                    "region": {"code": "", "name": None, "data": []}
                }

            # Récupérer les données
            department_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'department',
                    PublicSafety.territory_code == str(dep)
                )
            ).all()

            region_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'region',
                    PublicSafety.territory_code == str(geo_info.reg)
                )
            ).all()

            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {
                    "code": dep,
                    "name": f"Département {dep}",
                    "data": self._format_safety_data(department_data)
                },
                "region": {
                    "code": geo_info.reg,
                    "name": f"Région {geo_info.reg}",
                    "data": self._format_safety_data(region_data)
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_department: {str(e)}")
            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": dep, "name": None, "data": []},
                "region": {"code": "", "name": None, "data": []}
            }
        finally:
            self.close()

    def get_by_region(self, reg: str) -> Dict:
        """Récupère les données de sécurité pour une région"""
        try:
            # Récupérer les données
            region_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'region',
                    PublicSafety.territory_code == str(reg)
                )
            ).all()

            if not region_data:
                return {
                    "commune": {"code": "", "name": None, "data": []},
                    "department": {"code": "", "name": None, "data": []},
                    "region": {"code": reg, "name": None, "data": []}
                }

            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {
                    "code": reg,
                    "name": f"Région {reg}",
                    "data": self._format_safety_data(region_data)
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_region: {str(e)}")
            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {"code": reg, "name": None, "data": []}
            }
        finally:
            self.close()
