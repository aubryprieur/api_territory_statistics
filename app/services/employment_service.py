from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict
from app.database import SessionLocal
from app.models import Employment, GeoCode

class EmploymentService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def calculate_rates(self, data: list) -> Dict:
        """Calcule tous les taux à partir des données"""
        try:
            if not data:
                return {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }

            # Agréger les données
            women_total = sum(d.women_15_64 or 0 for d in data)
            women_active = sum(d.women_active_15_64 or 0 for d in data)
            women_employed = sum(d.women_employed_15_64 or 0 for d in data)
            women_part_time_25_54 = sum(d.women_part_time_25_54 or 0 for d in data)
            women_total_25_54 = sum(d.women_employees_25_54 or 0 for d in data)
            women_part_time_15_64 = sum(d.women_part_time_15_64 or 0 for d in data)
            women_total_15_64 = sum(d.women_employees_15_64 or 0 for d in data)

            # Calculer les taux
            activity_rate = (women_active / women_total * 100) if women_total > 0 else 0
            employment_rate = (women_employed / women_total * 100) if women_total > 0 else 0
            part_time_rate_25_54 = (women_part_time_25_54 / women_total_25_54 * 100) if women_total_25_54 > 0 else 0
            part_time_rate_15_64 = (women_part_time_15_64 / women_total_15_64 * 100) if women_total_15_64 > 0 else 0

            return {
                "activity_rate": round(float(activity_rate), 2),
                "employment_rate": round(float(employment_rate), 2),
                "part_time_rate_25_54": round(float(part_time_rate_25_54), 2),
                "part_time_rate_15_64": round(float(part_time_rate_15_64), 2)
            }
        except Exception as e:
            print(f"Erreur dans calculate_rates: {str(e)}")
            raise

    def get_commune_rates(self, code: str):
        """Récupère les taux pour une commune"""
        try:
            # Récupérer les informations géographiques
            geo_info = self.db.query(GeoCode).filter(GeoCode.codgeo == str(code)).first()
            if not geo_info:
                return {
                    "territory_type": "commune",
                    "code": code,
                    "name": "Commune inconnue",
                    "rates": {
                        "activity_rate": 0,
                        "employment_rate": 0,
                        "part_time_rate_25_54": 0,
                        "part_time_rate_15_64": 0
                    }
                }

            # Récupérer les données d'emploi
            data = self.db.query(Employment).filter(Employment.geo_code == str(code)).all()
            rates = self.calculate_rates(data)

            return {
                "territory_type": "commune",
                "code": code,
                "name": geo_info.libgeo,
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_commune_rates: {str(e)}")
            return {
                "territory_type": "commune",
                "code": code,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }
        finally:
            self.close()

    def get_epci_rates(self, epci: str):
        """Récupère les taux pour un EPCI"""
        try:
            # Récupérer les communes de l'EPCI
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()
            if not communes:
                return {
                    "territory_type": "epci",
                    "code": epci,
                    "name": "EPCI inconnu",
                    "rates": {
                        "activity_rate": 0,
                        "employment_rate": 0,
                        "part_time_rate_25_54": 0,
                        "part_time_rate_15_64": 0
                    }
                }

            commune_codes = [c[0] for c in communes]
            data = self.db.query(Employment).filter(Employment.geo_code.in_(commune_codes)).all()
            rates = self.calculate_rates(data)

            epci_name = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            name = epci_name[0] if epci_name else f"EPCI {epci}"

            return {
                "territory_type": "epci",
                "code": epci,
                "name": name,
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_epci_rates: {str(e)}")
            return {
                "territory_type": "epci",
                "code": epci,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }
        finally:
            self.close()

    def get_department_rates(self, dep: str):
        """Récupère les taux pour un département"""
        try:
            # Récupérer les communes du département
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.dep == str(dep)).all()
            if not communes:
                return {
                    "territory_type": "department",
                    "code": dep,
                    "name": "Département inconnu",
                    "rates": {
                        "activity_rate": 0,
                        "employment_rate": 0,
                        "part_time_rate_25_54": 0,
                        "part_time_rate_15_64": 0
                    }
                }

            commune_codes = [c[0] for c in communes]
            data = self.db.query(Employment).filter(Employment.geo_code.in_(commune_codes)).all()
            rates = self.calculate_rates(data)

            return {
                "territory_type": "department",
                "code": dep,
                "name": f"Département {dep}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_department_rates: {str(e)}")
            return {
                "territory_type": "department",
                "code": dep,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }
        finally:
            self.close()

    def get_region_rates(self, reg: str):
        """Récupère les taux pour une région"""
        try:
            # Récupérer les communes de la région
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == str(reg)).all()
            if not communes:
                return {
                    "territory_type": "region",
                    "code": reg,
                    "name": "Région inconnue",
                    "rates": {
                        "activity_rate": 0,
                        "employment_rate": 0,
                        "part_time_rate_25_54": 0,
                        "part_time_rate_15_64": 0
                    }
                }

            commune_codes = [c[0] for c in communes]
            data = self.db.query(Employment).filter(Employment.geo_code.in_(commune_codes)).all()
            rates = self.calculate_rates(data)

            return {
                "territory_type": "region",
                "code": reg,
                "name": f"Région {reg}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_region_rates: {str(e)}")
            return {
                "territory_type": "region",
                "code": reg,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }
        finally:
            self.close()

    def get_france_rates(self):
        """Récupère les taux pour la France entière"""
        try:
            data = self.db.query(Employment).all()
            rates = self.calculate_rates(data)

            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_france_rates: {str(e)}")
            return {
                "territory_type": "country",
                "code": "FR",
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }
        finally:
            self.close()
