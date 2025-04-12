from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.database import SessionLocal
from app.models import Population, GeoCode

class PopulationService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def get_by_code(self, codgeo: str):
        """Récupère la pyramide des âges d'une commune"""
        try:
            results = self.db.query(Population).filter(
                Population.codgeo == str(codgeo)
            ).all()

            return [
                {
                    "NIVGEO": r.nivgeo,
                    "CODGEO": r.codgeo,
                    "LIBGEO": r.libgeo,
                    "SEXE": r.sexe,
                    "AGED100": r.aged100,
                    "NB": r.nb
                }
                for r in results
            ]
        except Exception as e:
            print(f"Erreur lors de la récupération des données de population pour {codgeo}: {str(e)}")
            return []
        finally:
            self.close()

    def get_population_and_children_rate(self, code: str):
        """Calcule les taux d'enfants par tranches d'âge pour une commune"""
        try:
            # Requête pour la population totale
            total_pop = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo == str(code)
            ).scalar() or 0

            # Requête pour les enfants de moins de 3 ans
            under_3 = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo == str(code),
                Population.aged100.in_(['000', '001', '002'])
            ).scalar() or 0

            # Requête pour les enfants de 3 à 5 ans
            three_to_five = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo == str(code),
                Population.aged100.in_(['003', '004', '005'])
            ).scalar() or 0

            return {
                "total_population": float(total_pop),
                "children_under_3": float(under_3),
                "children_3_to_5": float(three_to_five),
                "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
                "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0
            }
        except Exception as e:
            print(f"Erreur lors du calcul des taux d'enfants pour {code}: {str(e)}")
            return {
                "total_population": 0.0,
                "children_under_3": 0.0,
                "children_3_to_5": 0.0,
                "under_3_rate": 0.0,
                "three_to_five_rate": 0.0
            }
        finally:
            self.close()

    def aggregate_children_by_epci(self, epci: str, geocode_service):
        """Agrège les statistiques des enfants pour un EPCI"""
        try:
            # Obtenir les communes de l'EPCI
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()
            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "total_population": 0.0,
                    "children_under_3": 0.0,
                    "children_3_to_5": 0.0,
                    "under_3_rate": 0.0,
                    "three_to_five_rate": 0.0,
                    "communes_count": 0
                }

            commune_codes = [c[0] for c in communes]

            # Requête pour la population totale
            total_pop = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes)
            ).scalar() or 0

            # Requête pour les enfants de moins de 3 ans
            under_3 = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes),
                Population.aged100.in_(['000', '001', '002'])
            ).scalar() or 0

            # Requête pour les enfants de 3 à 5 ans
            three_to_five = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes),
                Population.aged100.in_(['003', '004', '005'])
            ).scalar() or 0

            # Obtenir le nom de l'EPCI
            epci_info = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            return {
                "epci": epci,
                "epci_name": epci_name,
                "total_population": float(total_pop),
                "children_under_3": float(under_3),
                "children_3_to_5": float(three_to_five),
                "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
                "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
                "communes_count": len(commune_codes)
            }
        except Exception as e:
            print(f"Erreur lors de l'agrégation pour l'EPCI {epci}: {str(e)}")
            return {
                "epci": epci,
                "epci_name": "",
                "total_population": 0.0,
                "children_under_3": 0.0,
                "children_3_to_5": 0.0,
                "under_3_rate": 0.0,
                "three_to_five_rate": 0.0,
                "communes_count": 0
            }
        finally:
            self.close()

    def aggregate_children_by_department(self, dep: str, geocode_service):
        """Agrège les statistiques des enfants pour un département"""
        try:
            # Obtenir les communes du département
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.dep == str(dep)).all()
            if not communes:
                return {
                    "department": dep,
                    "total_population": 0.0,
                    "children_under_3": 0.0,
                    "children_3_to_5": 0.0,
                    "under_3_rate": 0.0,
                    "three_to_five_rate": 0.0,
                    "communes_count": 0
                }

            commune_codes = [c[0] for c in communes]

            # Requête pour la population totale
            total_pop = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes)
            ).scalar() or 0

            # Requête pour les enfants de moins de 3 ans
            under_3 = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes),
                Population.aged100.in_(['000', '001', '002'])
            ).scalar() or 0

            # Requête pour les enfants de 3 à 5 ans
            three_to_five = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes),
                Population.aged100.in_(['003', '004', '005'])
            ).scalar() or 0

            return {
                "department": dep,
                "total_population": float(total_pop),
                "children_under_3": float(under_3),
                "children_3_to_5": float(three_to_five),
                "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
                "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
                "communes_count": len(commune_codes)
            }
        except Exception as e:
            print(f"Erreur lors de l'agrégation pour le département {dep}: {str(e)}")
            return {
                "department": dep,
                "total_population": 0.0,
                "children_under_3": 0.0,
                "children_3_to_5": 0.0,
                "under_3_rate": 0.0,
                "three_to_five_rate": 0.0,
                "communes_count": 0
            }
        finally:
            self.close()

    def aggregate_children_by_region(self, reg: str, geocode_service):
        """Agrège les statistiques des enfants pour une région"""
        try:
            # Obtenir les communes de la région
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == str(reg)).all()
            if not communes:
                return {
                    "region": reg,
                    "total_population": 0.0,
                    "children_under_3": 0.0,
                    "children_3_to_5": 0.0,
                    "under_3_rate": 0.0,
                    "three_to_five_rate": 0.0,
                    "communes_count": 0,
                    "departments_count": 0
                }

            commune_codes = [c[0] for c in communes]

            # Requête pour la population totale
            total_pop = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes)
            ).scalar() or 0

            # Requête pour les enfants de moins de 3 ans
            under_3 = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes),
                Population.aged100.in_(['000', '001', '002'])
            ).scalar() or 0

            # Requête pour les enfants de 3 à 5 ans
            three_to_five = self.db.query(func.sum(Population.nb)).filter(
                Population.codgeo.in_(commune_codes),
                Population.aged100.in_(['003', '004', '005'])
            ).scalar() or 0

            # Compter les départements dans la région
            departments = self.db.query(GeoCode.dep).filter(GeoCode.reg == str(reg)).distinct().all()
            departments_count = len(departments)

            return {
                "region": reg,
                "total_population": float(total_pop),
                "children_under_3": float(under_3),
                "children_3_to_5": float(three_to_five),
                "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
                "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
                "communes_count": len(commune_codes),
                "departments_count": departments_count
            }
        except Exception as e:
            print(f"Erreur lors de l'agrégation pour la région {reg}: {str(e)}")
            return {
                "region": reg,
                "total_population": 0.0,
                "children_under_3": 0.0,
                "children_3_to_5": 0.0,
                "under_3_rate": 0.0,
                "three_to_five_rate": 0.0,
                "communes_count": 0,
                "departments_count": 0
            }
        finally:
            self.close()

    def aggregate_children_france(self, geocode_service):
        """Agrège les statistiques des enfants au niveau national"""
        try:
            # Requête pour la population totale
            total_pop = self.db.query(func.sum(Population.nb)).scalar() or 0

            # Requête pour les enfants de moins de 3 ans
            under_3 = self.db.query(func.sum(Population.nb)).filter(
                Population.aged100.in_(['000', '001', '002'])
            ).scalar() or 0

            # Requête pour les enfants de 3 à 5 ans
            three_to_five = self.db.query(func.sum(Population.nb)).filter(
                Population.aged100.in_(['003', '004', '005'])
            ).scalar() or 0

            # Compter les communes, départements et régions
            communes_count = self.db.query(func.count(GeoCode.codgeo)).scalar() or 0
            departments_count = self.db.query(func.count(func.distinct(GeoCode.dep))).scalar() or 0
            regions_count = self.db.query(func.count(func.distinct(GeoCode.reg))).scalar() or 0

            return {
                "total_population": float(total_pop),
                "children_under_3": float(under_3),
                "children_3_to_5": float(three_to_five),
                "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
                "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
                "communes_count": communes_count,
                "departments_count": departments_count,
                "regions_count": regions_count
            }
        except Exception as e:
            print(f"Erreur lors de l'agrégation pour la France: {str(e)}")
            return {
                "total_population": 0.0,
                "children_under_3": 0.0,
                "children_3_to_5": 0.0,
                "under_3_rate": 0.0,
                "three_to_five_rate": 0.0,
                "communes_count": 0,
                "departments_count": 0,
                "regions_count": 0
            }
        finally:
            self.close()


    def _safe_float(self, value):
        """Convertit une valeur en float de manière sécurisée"""
        try:
            if value is None:
                return 0.0
            float_val = float(value)
            return float_val
        except (ValueError, TypeError):
            return 0.0

    def get_children_by_epci_communes(self, epci: str, geocode_service):
        """Récupère les statistiques des enfants pour toutes les communes d'un EPCI"""
        try:
            # Obtenir les communes de l'EPCI
            communes = self.db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "communes_count": 0,
                    "communes": []
                }

            # Récupérer les données pour chaque commune
            communes_data = []
            for code, name in communes:
                commune_data = self.get_population_and_children_rate(code)
                commune_data["code"] = code
                commune_data["name"] = name
                communes_data.append(commune_data)

            # Obtenir le nom de l'EPCI
            epci_info = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            return {
                "epci": epci,
                "epci_name": epci_name,
                "communes_count": len(communes),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des données des communes pour l'EPCI {epci}: {str(e)}")
            return {
                "epci": epci,
                "epci_name": "",
                "communes_count": 0,
                "communes": []
            }
        finally:
            self.close()

    def get_epci_population(self, epci: str):
        """Récupère la pyramide des âges d'un EPCI en agrégeant les communes membres"""
        try:
            # Récupérer les communes de l'EPCI
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "communes_count": 0,
                    "total_population": 0,
                    "men_count": 0,
                    "women_count": 0,
                    "population_by_age": {},
                    "communes": []
                }

            commune_codes = [c[0] for c in communes]

            # Récupérer le nom de l'EPCI
            epci_info = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # Récupérer les données agrégées par sexe et âge pour toutes les communes de l'EPCI
            population_data = self.db.query(
                Population.aged100,
                Population.sexe,
                func.sum(Population.nb).label('total')
            ).filter(
                Population.codgeo.in_(commune_codes)
            ).group_by(
                Population.aged100,
                Population.sexe
            ).all()

            # Préparer la structure pour la réponse
            population_by_age = {}
            men_count = 0
            women_count = 0
            total_population = 0

            # Initialiser la structure avec tous les âges de 0 à 100
            for age in range(101):  # 0 à 100 inclus
                age_str = str(age).zfill(3)  # Formater comme '000', '001', ..., '100'
                population_by_age[age_str] = {"total": 0, "men": 0, "women": 0, "age": age}

            # Organiser les données par âge et sexe
            for age, sexe, count in population_data:
                count_float = self._safe_float(count)
                total_population += count_float

                # Différencier par sexe
                if sexe == "1":  # Homme
                    men_count += count_float
                elif sexe == "2":  # Femme
                    women_count += count_float

                # Ajouter à la structure par âge
                if age in population_by_age:
                    population_by_age[age]["total"] += count_float

                    if sexe == "1":
                        population_by_age[age]["men"] += count_float
                    elif sexe == "2":
                        population_by_age[age]["women"] += count_float

            # Récupérer la liste complète des communes avec leur population
            communes_info = []
            for code in commune_codes:
                commune_name = self.db.query(GeoCode.libgeo).filter(GeoCode.codgeo == code).first()
                commune_pop = self.db.query(func.sum(Population.nb)).filter(Population.codgeo == code).scalar() or 0

                communes_info.append({
                    "code": code,
                    "name": commune_name[0] if commune_name else f"Commune {code}",
                    "population": float(commune_pop)
                })

            # Trier les communes par population décroissante
            communes_info.sort(key=lambda x: x["population"], reverse=True)

            # Convertir le dictionnaire population_by_age en liste pour faciliter l'accès âge par âge
            population_by_age_list = []
            for age in range(101):  # 0 à 100 inclus
                age_str = str(age).zfill(3)
                if age_str in population_by_age:
                    data = population_by_age[age_str]
                    population_by_age_list.append({
                        "age": age,
                        "total": data["total"],
                        "men": data["men"],
                        "women": data["women"]
                    })

            return {
                "epci": epci,
                "epci_name": epci_name,
                "communes_count": len(commune_codes),
                "total_population": total_population,
                "men_count": men_count,
                "women_count": women_count,
                "gender_ratio": {
                    "men_percentage": round(men_count / total_population * 100, 2) if total_population > 0 else 0,
                    "women_percentage": round(women_count / total_population * 100, 2) if total_population > 0 else 0
                },
                "population_by_age": population_by_age_list,  # Liste ordonnée par âge croissant
                "communes": communes_info
            }
        except Exception as e:
            print(f"Erreur lors de l'agrégation de la population pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "epci": epci,
                "epci_name": "",
                "communes_count": 0,
                "total_population": 0,
                "men_count": 0,
                "women_count": 0,
                "population_by_age": [],
                "communes": []
            }
        finally:
            self.close()
