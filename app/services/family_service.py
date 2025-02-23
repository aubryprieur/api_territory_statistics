import math
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
from app.models import Family, GeoCode


class FamilyService:
    def __init__(self):
        """ Initialise la connexion à la base de données """
        self.db = SessionLocal()

    def close(self):
        """ Ferme la session de base de données proprement """
        self.db.close()

    def _safe_float(self, value):
        """Convertit une valeur en float de manière sécurisée"""
        try:
            if value is None:
                return 0.0
            float_val = float(value)
            if math.isnan(float_val) or math.isinf(float_val):
                return 0.0
            return float_val
        except (TypeError, ValueError):
            return 0.0

    def get_families_by_commune(self, geo_code: str, start_year: int = None, end_year: int = None):
        """ Récupère les données des familles pour une commune donnée """
        try:
            results = self.db.query(Family).filter(Family.geo_code == geo_code).all()
            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            self.close()

    def get_families_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées par EPCI """
        try:
            # Connexion à la base de données
            db = SessionLocal()

            # Récupérer toutes les communes de l'EPCI
            communes = [geo.codgeo for geo in db.query(GeoCode).filter(GeoCode.epci == epci).all()]
            if not communes:
                return {"error": "Aucune commune trouvée pour cet EPCI"}

            # Récupérer les données des familles pour toutes les communes de l'EPCI
            results = db.query(Family).filter(Family.geo_code.in_(communes)).all()

            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def get_families_by_department(self, dep: str, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées par département """
        try:
            # Connexion à la base de données
            db = SessionLocal()

            # Récupérer toutes les communes du département
            communes = [geo.codgeo for geo in db.query(GeoCode).filter(GeoCode.dep == dep).all()]
            if not communes:
                return {"error": "Aucune commune trouvée pour ce département"}

            # Récupérer les données des familles pour toutes les communes du département
            results = db.query(Family).filter(Family.geo_code.in_(communes)).all()

            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def get_families_by_region(self, reg: str, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées par région """
        try:
            db = SessionLocal()

            # Le reg est maintenant comparé en tant que string
            communes = [geo.codgeo for geo in db.query(GeoCode).filter(GeoCode.reg == str(reg)).all()]
            if not communes:
                return {"error": "Aucune commune trouvée pour cette région"}

            results = db.query(Family).filter(Family.geo_code.in_(communes)).all()
            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def get_families_france(self, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées pour toute la France """
        try:
            results = self.db.query(Family).all()
            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            self.close()

    def _format_response(self, results, start_year=None, end_year=None):
        """Formate les résultats et calcule l'évolution si nécessaire"""
        if not results:
            return {"error": "Aucune donnée disponible"}

        # Organisation des données par année
        data_by_year = {}
        for f in results:
            if f.year not in data_by_year:
                data_by_year[f.year] = {
                    "total_families": 0.0,
                    "couples_with_children": 0.0,
                    "single_parent_families": 0.0,
                    "single_fathers": 0.0,
                    "single_mothers": 0.0,
                    "couples_without_children": 0.0
                }

            # Utiliser _safe_float pour les valeurs
            data_by_year[f.year]["total_families"] += self._safe_float(f.total_households)
            data_by_year[f.year]["couples_with_children"] += self._safe_float(f.couples_with_children)
            data_by_year[f.year]["single_parent_families"] += self._safe_float(f.single_parent_families)
            data_by_year[f.year]["single_fathers"] += self._safe_float(f.single_fathers)
            data_by_year[f.year]["single_mothers"] += self._safe_float(f.single_mothers)
            data_by_year[f.year]["couples_without_children"] += self._safe_float(f.couples_without_children)

        # Calcul des évolutions si demandé
        evolution = self._calculate_evolution(data_by_year, start_year, end_year)

        return {
            "family_data": data_by_year,
            "evolution": evolution
        }

    def _calculate_evolution(self, data, start_year, end_year):
        """Calcule l'évolution des familles entre deux années"""
        years = sorted(data.keys())
        if not years:
            return {"error": "Aucune donnée disponible pour l'évolution"}

        start_year = start_year or years[0]
        end_year = end_year or years[-1]

        if start_year not in years or end_year not in years:
            return {"error": f"Les années doivent être comprises entre {years[0]} et {years[-1]}"}

        evolutions = {}
        metrics = ["total_families", "couples_with_children", "single_parent_families",
                  "single_fathers", "single_mothers", "couples_without_children"]

        for metric in metrics:
            try:
                value_start = self._safe_float(data[start_year][metric])
                value_end = self._safe_float(data[end_year][metric])

                if value_start > 0:
                    evolution = ((value_end - value_start) / value_start * 100)
                    evolution = round(self._safe_float(evolution), 1)
                else:
                    evolution = 0.0
            except:
                evolution = 0.0

            evolutions[metric] = {
                "start_value": value_start,
                "end_value": value_end,
                "evolution_percentage": evolution,
                "period": f"{start_year}-{end_year}"
            }

        return evolutions
