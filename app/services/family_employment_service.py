from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, List, Optional
from app.database import SessionLocal
from app.models import FamilyEmployment, GeoCode

class FamilyEmploymentService:
    def __init__(self):
        self.db = SessionLocal()

        # Dictionnaire des libellés TF12
        self.tf12_labels = {
            "11": "Famille monoparentale - Homme actif ayant un emploi",
            "12": "Famille monoparentale - Homme sans emploi",
            "21": "Famille monoparentale - Femme active ayant un emploi",
            "22": "Famille monoparentale - Femme sans emploi",
            "41": "Couple avec enfant(s) - Deux parents actifs ayant un emploi",
            "42": "Couple avec enfant(s) - Homme actif ayant un emploi, conjoint sans emploi",
            "43": "Couple avec enfant(s) - Femme active ayant un emploi, conjoint sans emploi",
            "44": "Couple avec enfant(s) - Aucun parent actif ayant un emploi"
        }

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def get_available_years(self):
        """Récupère les années disponibles dans la base de données"""
        try:
            years = self.db.query(FamilyEmployment.year).distinct().order_by(FamilyEmployment.year).all()
            return [year[0] for year in years]
        except Exception as e:
            print(f"Erreur lors de la récupération des années disponibles: {str(e)}")
            return [2021]  # Valeur par défaut en cas d'erreur
        finally:
            self.close()

    def _calculate_distribution(self, data, age_group="0"):
        """Calcule la répartition des TF12 pour un groupe d'âge spécifié"""
        try:
            # Calculer le total
            total = sum(row.number for row in data)

            # Calculer les pourcentages pour chaque TF12
            distributions = {}
            if total > 0:
                # Récupérer tous les TF12 uniques
                unique_tf12 = sorted({row.tf12 for row in data})

                for tf12 in unique_tf12:
                    count = sum(row.number for row in data if row.tf12 == tf12)
                    percentage = (count / total * 100) if total > 0 else 0

                    key = self.tf12_labels.get(tf12, f"Type {tf12}")
                    distributions[key] = {
                        "code": str(tf12),
                        "count": float(count),
                        "percentage": round(float(percentage), 1)
                    }

            return {
                "total_count": float(total),
                "distributions": distributions,
                "age_group": "0-2 ans" if age_group == "0" else "3-5 ans"
            }
        except Exception as e:
            print(f"Erreur dans le calcul de la distribution: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "total_count": 0,
                "distributions": {},
                "age_group": "0-2 ans" if age_group == "0" else "3-5 ans"
            }

    def get_commune_distribution(self, code: str, age_group="0", year=None):
        """Récupère la distribution pour une commune"""
        try:
            # Récupérer l'année la plus récente si non spécifiée
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            # Vérifier si la commune existe
            geo_info = self.db.query(GeoCode).filter(GeoCode.codgeo == str(code)).first()
            if not geo_info:
                return {
                    "territory_type": "commune",
                    "code": code,
                    "name": "Commune inconnue",
                    "data": {}
                }

            results = {}

            # Récupérer les données pour l'année spécifiée
            commune_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.geo_code == str(code),
                FamilyEmployment.age_group == age_group,
                FamilyEmployment.year == year
            ).all()

            if commune_data:
                results[year] = self._calculate_distribution(commune_data, age_group)
            else:
                print(f"Aucune donnée trouvée pour la commune {code}, année {year}, groupe d'âge {age_group}")

            return {
                "territory_type": "commune",
                "code": code,
                "name": geo_info.libgeo,
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la commune {code}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "territory_type": "commune",
                "code": code,
                "name": "Erreur",
                "data": {}
            }
        finally:
            self.close()

    def get_epci_distribution(self, epci: str, age_group="0", year=None):
        """Récupère la distribution pour un EPCI"""
        try:
            # Récupérer l'année la plus récente si non spécifiée
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            # Récupérer les communes de l'EPCI
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()
            if not communes:
                return {
                    "territory_type": "epci",
                    "code": epci,
                    "name": "EPCI inconnu",
                    "data": {}
                }

            commune_codes = [c[0] for c in communes]
            results = {}

            # Récupérer les données de la base
            epci_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.geo_code.in_(commune_codes),
                FamilyEmployment.age_group == age_group,
                FamilyEmployment.year == year
            ).all()

            if epci_data:
                results[year] = self._calculate_distribution(epci_data, age_group)

            # Obtenir le nom de l'EPCI
            epci_name = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()

            return {
                "territory_type": "epci",
                "code": epci,
                "name": epci_name[0] if epci_name else f"EPCI {epci}",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour l'EPCI {epci}: {str(e)}")
            return {
                "territory_type": "epci",
                "code": epci,
                "name": "Erreur",
                "data": {}
            }
        finally:
            self.close()

    def get_department_distribution(self, dep: str, age_group="0", year=None):
        """Récupère la distribution pour un département"""
        try:
            # Récupérer l'année la plus récente si non spécifiée
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            # Récupérer les communes du département
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.dep == str(dep)).all()
            if not communes:
                return {
                    "territory_type": "department",
                    "code": dep,
                    "name": "Département inconnu",
                    "data": {}
                }

            commune_codes = [c[0] for c in communes]
            results = {}

            # Récupérer les données de la base
            dep_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.geo_code.in_(commune_codes),
                FamilyEmployment.age_group == age_group,
                FamilyEmployment.year == year
            ).all()

            if dep_data:
                results[year] = self._calculate_distribution(dep_data, age_group)

            return {
                "territory_type": "department",
                "code": dep,
                "name": f"Département {dep}",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour le département {dep}: {str(e)}")
            return {
                "territory_type": "department",
                "code": dep,
                "name": "Erreur",
                "data": {}
            }
        finally:
            self.close()

    def get_region_distribution(self, reg: str, age_group="0", year=None):
        """Récupère la distribution pour une région"""
        try:
            # Récupérer l'année la plus récente si non spécifiée
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            # Récupérer les communes de la région
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == str(reg)).all()
            if not communes:
                return {
                    "territory_type": "region",
                    "code": reg,
                    "name": "Région inconnue",
                    "data": {}
                }

            commune_codes = [c[0] for c in communes]
            results = {}

            # Récupérer les données de la base
            reg_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.geo_code.in_(commune_codes),
                FamilyEmployment.age_group == age_group,
                FamilyEmployment.year == year
            ).all()

            if reg_data:
                results[year] = self._calculate_distribution(reg_data, age_group)

            return {
                "territory_type": "region",
                "code": reg,
                "name": f"Région {reg}",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la région {reg}: {str(e)}")
            return {
                "territory_type": "region",
                "code": reg,
                "name": "Erreur",
                "data": {}
            }
        finally:
            self.close()

    def get_france_distribution(self, age_group="0", year=None):
        """Récupère la distribution pour la France entière"""
        try:
            # Récupérer l'année la plus récente si non spécifiée
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            results = {}

            # Récupérer toutes les données nationales pour l'année et le groupe d'âge spécifiés
            france_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.age_group == age_group,
                FamilyEmployment.year == year
            ).all()

            if france_data:
                results[year] = self._calculate_distribution(france_data, age_group)

            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la France: {str(e)}")
            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "data": {}
            }
        finally:
            self.close()
