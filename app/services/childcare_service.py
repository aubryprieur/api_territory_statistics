from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import Dict, Optional, List, Any
from app.database import SessionLocal
from app.models import Childcare

class ChildcareService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def get_coverage_by_commune(self, commune: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour une commune depuis la base de données"""
        try:
            # Construire la requête de base
            query = self.db.query(Childcare).filter(
                Childcare.territory_type == 'commune',
                Childcare.territory_code == str(commune)
            ).order_by(Childcare.year.desc())  # Tri par année décroissante pour avoir les plus récentes d'abord

            # Filtrer par année si spécifié
            if start_year and end_year:
                query = query.filter(
                    Childcare.year >= start_year,
                    Childcare.year <= end_year
                )

            # Exécuter la requête
            results = query.all()

            if not results:
                return {"error": "Commune non trouvée dans les données"}

            # Formater les résultats
            result = {}
            for record in results:
                year = record.year
                result[year] = {
                    "commune_name": record.territory_name,
                    "epci": {
                        "code": record.parent_code,
                        "name": record.parent_name
                    },
                    "department": {
                        "code": None,  # Nous n'avons pas cette information directement
                        "name": None
                    },
                    "coverage_rates": {
                        "eaje_psu": record.eaje_psu if record.eaje_psu is not None else 0.0,
                        "eaje_hors_psu": record.eaje_hors_psu if record.eaje_hors_psu is not None else 0.0,
                        "eaje_total": record.eaje_total if record.eaje_total is not None else 0.0,
                        "preschool": record.preschool if record.preschool is not None else 0.0,
                        "childminder": record.childminder if record.childminder is not None else 0.0,
                        "home_care": record.home_care if record.home_care is not None else 0.0,
                        "individual_total": record.individual_total if record.individual_total is not None else 0.0,
                        "global": record.global_rate if record.global_rate is not None else 0.0
                    }
                }

            return {
                "commune": commune,
                "coverage_data": result,
                "data_source": "database"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_commune: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()

    def get_coverage_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour un EPCI depuis la base de données"""
        try:
            # Construire la requête de base
            query = self.db.query(Childcare).filter(
                Childcare.territory_type == 'epci',
                Childcare.territory_code == str(epci)
            ).order_by(Childcare.year.desc())

            # Filtrer par année si spécifié
            if start_year and end_year:
                query = query.filter(
                    Childcare.year >= start_year,
                    Childcare.year <= end_year
                )

            # Exécuter la requête
            results = query.all()

            if not results:
                return {"error": f"EPCI {epci} non trouvé"}

            # Formater les résultats
            result = {}
            for record in results:
                year = record.year
                result[year] = {
                    "territory_name": record.territory_name,
                    "department": {
                        "code": record.parent_code,
                        "name": record.parent_name
                    },
                    "coverage_rates": {
                        "eaje_psu": record.eaje_psu if record.eaje_psu is not None else 0.0,
                        "eaje_hors_psu": record.eaje_hors_psu if record.eaje_hors_psu is not None else 0.0,
                        "eaje_total": record.eaje_total if record.eaje_total is not None else 0.0,
                        "preschool": record.preschool if record.preschool is not None else 0.0,
                        "childminder": record.childminder if record.childminder is not None else 0.0,
                        "home_care": record.home_care if record.home_care is not None else 0.0,
                        "individual_total": record.individual_total if record.individual_total is not None else 0.0,
                        "global": record.global_rate if record.global_rate is not None else 0.0
                    }
                }

            return {
                "epci": epci,
                "coverage_data": result,
                "data_source": "database"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_epci: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()

    def get_coverage_by_department(self, dep: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour un département depuis la base de données"""
        try:
            # Construire la requête de base
            query = self.db.query(Childcare).filter(
                Childcare.territory_type == 'department',
                Childcare.territory_code == str(dep)
            ).order_by(Childcare.year.desc())

            # Filtrer par année si spécifié
            if start_year and end_year:
                query = query.filter(
                    Childcare.year >= start_year,
                    Childcare.year <= end_year
                )

            # Exécuter la requête
            results = query.all()

            if not results:
                return {"error": f"Département {dep} non trouvé"}

            # Formater les résultats
            result = {}
            for record in results:
                year = record.year
                result[year] = {
                    "territory_name": record.territory_name,
                    "region": {
                        "code": record.parent_code,
                        "name": record.parent_name
                    },
                    "coverage_rates": {
                        "eaje_psu": record.eaje_psu if record.eaje_psu is not None else 0.0,
                        "eaje_hors_psu": record.eaje_hors_psu if record.eaje_hors_psu is not None else 0.0,
                        "eaje_total": record.eaje_total if record.eaje_total is not None else 0.0,
                        "preschool": record.preschool if record.preschool is not None else 0.0,
                        "childminder": record.childminder if record.childminder is not None else 0.0,
                        "home_care": record.home_care if record.home_care is not None else 0.0,
                        "individual_total": record.individual_total if record.individual_total is not None else 0.0,
                        "global": record.global_rate if record.global_rate is not None else 0.0
                    }
                }

            return {
                "department": dep,
                "coverage_data": result,
                "data_source": "database"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_department: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()

    def get_coverage_by_region(self, reg: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour une région depuis la base de données"""
        try:
            # Construire la requête de base
            query = self.db.query(Childcare).filter(
                Childcare.territory_type == 'region',
                Childcare.territory_code == str(reg)
            ).order_by(Childcare.year.desc())

            # Filtrer par année si spécifié
            if start_year and end_year:
                query = query.filter(
                    Childcare.year >= start_year,
                    Childcare.year <= end_year
                )

            # Exécuter la requête
            results = query.all()

            if not results:
                return {"error": f"Région {reg} non trouvée"}

            # Formater les résultats
            result = {}
            for record in results:
                year = record.year
                result[year] = {
                    "territory_name": record.territory_name,
                    "coverage_rates": {
                        "eaje_psu": record.eaje_psu if record.eaje_psu is not None else 0.0,
                        "eaje_hors_psu": record.eaje_hors_psu if record.eaje_hors_psu is not None else 0.0,
                        "eaje_total": record.eaje_total if record.eaje_total is not None else 0.0,
                        "preschool": record.preschool if record.preschool is not None else 0.0,
                        "childminder": record.childminder if record.childminder is not None else 0.0,
                        "home_care": record.home_care if record.home_care is not None else 0.0,
                        "individual_total": record.individual_total if record.individual_total is not None else 0.0,
                        "global": record.global_rate if record.global_rate is not None else 0.0
                    }
                }

            return {
                "region": reg,
                "coverage_data": result,
                "data_source": "database"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_region: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()

    def get_coverage_france(self, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour la France entière depuis la base de données"""
        try:
            # Construire la requête de base
            query = self.db.query(Childcare).filter(
                Childcare.territory_type == 'france'
            ).order_by(Childcare.year.desc())

            # Filtrer par année si spécifié
            if start_year and end_year:
                query = query.filter(
                    Childcare.year >= start_year,
                    Childcare.year <= end_year
                )

            # Exécuter la requête
            results = query.all()

            if not results:
                return {"error": "Données nationales non disponibles"}

            # Formater les résultats
            result = {}
            for record in results:
                year = record.year
                result[year] = {
                    "territory_name": record.territory_name or "France entière",
                    "coverage_rates": {
                        "eaje_psu": record.eaje_psu if record.eaje_psu is not None else 0.0,
                        "eaje_hors_psu": record.eaje_hors_psu if record.eaje_hors_psu is not None else 0.0,
                        "eaje_total": record.eaje_total if record.eaje_total is not None else 0.0,
                        "preschool": record.preschool if record.preschool is not None else 0.0,
                        "childminder": record.childminder if record.childminder is not None else 0.0,
                        "home_care": record.home_care if record.home_care is not None else 0.0,
                        "individual_total": record.individual_total if record.individual_total is not None else 0.0,
                        "global": record.global_rate if record.global_rate is not None else 0.0
                    }
                }

            return {
                "coverage_data": result,
                "data_source": "database"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_france: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()

    def get_evolution_by_territory_type(self, territory_type: str, start_year: int, end_year: int):
        """
        Calcule l'évolution des taux de couverture entre deux années pour tous les territoires d'un type donné
        Utile pour les analyses comparatives
        """
        try:
            # Vérifier les années
            if not start_year or not end_year or start_year >= end_year:
                return {"error": "Années invalides pour le calcul d'évolution"}

            # Requête pour récupérer les données de l'année de début
            start_query = self.db.query(
                Childcare.territory_code,
                Childcare.territory_name,
                Childcare.global_rate.label('start_rate')
            ).filter(
                Childcare.territory_type == territory_type,
                Childcare.year == start_year
            ).subquery()

            # Requête pour récupérer les données de l'année de fin
            end_query = self.db.query(
                Childcare.territory_code,
                Childcare.territory_name,
                Childcare.global_rate.label('end_rate')
            ).filter(
                Childcare.territory_type == territory_type,
                Childcare.year == end_year
            ).subquery()

            # Joindre les deux requêtes pour calculer l'évolution
            evolution_data = self.db.query(
                start_query.c.territory_code,
                start_query.c.territory_name,
                start_query.c.start_rate,
                end_query.c.end_rate,
                ((end_query.c.end_rate - start_query.c.start_rate) / start_query.c.start_rate * 100).label('evolution_percent')
            ).join(
                end_query,
                start_query.c.territory_code == end_query.c.territory_code
            ).order_by(desc('evolution_percent')).all()

            # Formater les résultats
            results = []
            for item in evolution_data:
                if item.start_rate is not None and item.end_rate is not None:
                    results.append({
                        "territory_code": item.territory_code,
                        "territory_name": item.territory_name,
                        "start_year": start_year,
                        "end_year": end_year,
                        "start_rate": round(item.start_rate, 1),
                        "end_rate": round(item.end_rate, 1),
                        "evolution_percent": round(item.evolution_percent, 1) if item.evolution_percent is not None else None
                    })

            return {
                "territory_type": territory_type,
                "period": f"{start_year}-{end_year}",
                "evolution_data": results
            }

        except Exception as e:
            print(f"Erreur dans get_evolution_by_territory_type: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()

    def get_comparative_data(self, territory_codes: List[str], territory_type: str, year: int = None):
        """
        Récupère des données comparatives pour plusieurs territoires du même type
        Utile pour les tableaux de bord de comparaison
        """
        try:
            # Si aucune année spécifiée, prendre la plus récente disponible
            if year is None:
                latest_year = self.db.query(func.max(Childcare.year)).filter(
                    Childcare.territory_type == territory_type
                ).scalar()
                year = latest_year if latest_year else 2021

            # Requête pour récupérer les données
            results = self.db.query(Childcare).filter(
                Childcare.territory_type == territory_type,
                Childcare.territory_code.in_(territory_codes),
                Childcare.year == year
            ).all()

            # Formater les résultats
            comparative_data = {}
            for record in results:
                comparative_data[record.territory_code] = {
                    "name": record.territory_name,
                    "year": record.year,
                    "coverage_rates": {
                        "eaje_psu": record.eaje_psu if record.eaje_psu is not None else 0.0,
                        "eaje_hors_psu": record.eaje_hors_psu if record.eaje_hors_psu is not None else 0.0,
                        "eaje_total": record.eaje_total if record.eaje_total is not None else 0.0,
                        "preschool": record.preschool if record.preschool is not None else 0.0,
                        "childminder": record.childminder if record.childminder is not None else 0.0,
                        "home_care": record.home_care if record.home_care is not None else 0.0,
                        "individual_total": record.individual_total if record.individual_total is not None else 0.0,
                        "global": record.global_rate if record.global_rate is not None else 0.0
                    }
                }

            return {
                "territory_type": territory_type,
                "year": year,
                "territories": comparative_data
            }

        except Exception as e:
            print(f"Erreur dans get_comparative_data: {str(e)}")
            return {"error": str(e)}
        finally:
            self.close()
