import math
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
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
                    "couples_without_children": 0.0,
                    # Familles nombreuses
                    "families_with_3_children": 0.0,
                    "families_with_4_plus_children": 0.0,
                    "total_large_families": 0.0,
                }

            # Utiliser _safe_float pour les valeurs
            data_by_year[f.year]["total_families"] += self._safe_float(f.total_households)
            data_by_year[f.year]["couples_with_children"] += self._safe_float(f.couples_with_children)
            data_by_year[f.year]["single_parent_families"] += self._safe_float(f.single_parent_families)
            data_by_year[f.year]["single_fathers"] += self._safe_float(f.single_fathers)
            data_by_year[f.year]["single_mothers"] += self._safe_float(f.single_mothers)
            data_by_year[f.year]["couples_without_children"] += self._safe_float(f.couples_without_children)

            # Familles nombreuses
            data_by_year[f.year]["families_with_3_children"] += self._safe_float(f.children_under_24_three_siblings)
            data_by_year[f.year]["families_with_4_plus_children"] += self._safe_float(f.children_under_24_four_or_more_siblings)

        # Calculer les totaux et pourcentages APRÈS avoir accumulé toutes les données
        for year, data in data_by_year.items():
            # Calculer le total des familles nombreuses
            data["total_large_families"] = data["families_with_3_children"] + data["families_with_4_plus_children"]

            # Calculer tous les pourcentages
            total_families = data["total_families"]
            if total_families > 0:
                # Pourcentage existant (familles nombreuses)
                data["large_families_percentage"] = round(
                    (data["total_large_families"] / total_families) * 100, 2
                )

                # Nouveaux pourcentages demandés
                data["couples_with_children_percentage"] = round(
                    (data["couples_with_children"] / total_families) * 100, 2
                )
                data["single_parent_families_percentage"] = round(
                    (data["single_parent_families"] / total_families) * 100, 2
                )
                data["couples_without_children_percentage"] = round(
                    (data["couples_without_children"] / total_families) * 100, 2
                )

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
      # Ajouter les nouvelles métriques à la liste
      metrics = ["total_families", "couples_with_children", "couples_with_children_percentage",
                "single_parent_families", "single_parent_families_percentage",
                "single_fathers", "single_mothers", "couples_without_children",
                "couples_without_children_percentage",
                "families_with_3_children", "families_with_4_plus_children",
                "total_large_families", "large_families_percentage"]

      for metric in metrics:
          try:
              value_start = self._safe_float(data[start_year].get(metric, 0))
              value_end = self._safe_float(data[end_year].get(metric, 0))

              if value_start > 0:
                  evolution = ((value_end - value_start) / value_start * 100)
                  evolution = round(self._safe_float(evolution), 2)
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

    def get_couples_with_children_by_epci(self, epci: str):
        """Récupère les statistiques des couples avec enfants pour toutes les communes d'un EPCI"""
        try:
            # Établir une connexion à la base de données
            db = SessionLocal()

            # Récupérer les communes de l'EPCI
            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "year": 2021,  # Valeur par défaut
                    "communes_count": 0,
                    "total_households": 0.0,
                    "total_couples_with_children": 0.0,
                    "epci_couples_with_children_percentage": 0.0,
                    "communes": []
                }

            # Récupérer le nom de l'EPCI
            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # Récupérer l'année la plus récente disponible
            latest_year = db.query(func.max(Family.year)).scalar() or 2021

            # Récupérer les données pour chaque commune
            communes_data = []
            total_households = 0
            total_couples_with_children = 0

            for code, name in communes:
                # Récupérer les données familiales pour cette commune et l'année la plus récente
                commune_data = db.query(Family).filter(
                    Family.geo_code == code,
                    Family.year == latest_year
                ).first()

                if commune_data:
                    # Calculer le pourcentage de couples avec enfants
                    commune_households = self._safe_float(commune_data.total_households)
                    commune_couples_with_children = self._safe_float(commune_data.couples_with_children)
                    percentage = (commune_couples_with_children / commune_households * 100) if commune_households > 0 else 0

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": commune_households,
                        "couples_with_children": commune_couples_with_children,
                        "couples_with_children_percentage": round(percentage, 2)
                    })

                    # Additionner pour le calcul de la moyenne EPCI
                    total_households += commune_households
                    total_couples_with_children += commune_couples_with_children
                else:
                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": 0.0,
                        "couples_with_children": 0.0,
                        "couples_with_children_percentage": 0.0
                    })

            # Calculer la moyenne pour l'EPCI
            epci_percentage = (total_couples_with_children / total_households * 100) if total_households > 0 else 0

            # Trier par pourcentage décroissant
            communes_data.sort(key=lambda x: x["couples_with_children_percentage"], reverse=True)

            return {
                "epci": epci,
                "epci_name": epci_name,
                "year": latest_year,
                "communes_count": len(communes),
                "total_households": total_households,
                "total_couples_with_children": total_couples_with_children,
                "epci_couples_with_children_percentage": round(epci_percentage, 2),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des données des couples avec enfants pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Retourner une structure valide avec des valeurs par défaut
            return {
                "epci": epci,
                "epci_name": "",
                "year": 2021,  # Valeur par défaut
                "communes_count": 0,
                "total_households": 0.0,
                "total_couples_with_children": 0.0,
                "epci_couples_with_children_percentage": 0.0,
                "communes": []
            }
        finally:
            db.close()

    def get_single_parent_families_by_epci(self, epci: str):
        """Récupère les statistiques des familles monoparentales pour toutes les communes d'un EPCI"""
        try:
            # Établir une connexion à la base de données
            db = SessionLocal()

            # Récupérer les communes de l'EPCI
            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "year": 2021,  # Valeur par défaut
                    "communes_count": 0,
                    "total_households": 0.0,
                    "total_single_parent_families": 0.0,
                    "total_single_fathers": 0.0,
                    "total_single_mothers": 0.0,
                    "epci_single_parent_percentage": 0.0,
                    "epci_single_father_percentage": 0.0,
                    "epci_single_mother_percentage": 0.0,
                    "communes": []
                }

            # Récupérer le nom de l'EPCI
            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # Récupérer l'année la plus récente disponible
            latest_year = db.query(func.max(Family.year)).scalar() or 2021

            # Récupérer les données pour chaque commune
            communes_data = []
            total_households = 0
            total_single_parent_families = 0
            total_single_fathers = 0
            total_single_mothers = 0

            for code, name in communes:
                # Récupérer les données familiales pour cette commune et l'année la plus récente
                commune_data = db.query(Family).filter(
                    Family.geo_code == code,
                    Family.year == latest_year
                ).first()

                if commune_data:
                    # Récupérer les valeurs en sécurisant les None
                    commune_households = self._safe_float(commune_data.total_households)
                    commune_single_parent = self._safe_float(commune_data.single_parent_families)
                    commune_single_fathers = self._safe_float(commune_data.single_fathers)
                    commune_single_mothers = self._safe_float(commune_data.single_mothers)

                    # Calculer les pourcentages
                    total_percentage = (commune_single_parent / commune_households * 100) if commune_households > 0 else 0
                    fathers_percentage = (commune_single_fathers / commune_single_parent * 100) if commune_single_parent > 0 else 0
                    mothers_percentage = (commune_single_mothers / commune_single_parent * 100) if commune_single_parent > 0 else 0

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": commune_households,
                        "single_parent_families": commune_single_parent,
                        "single_fathers": commune_single_fathers,
                        "single_mothers": commune_single_mothers,
                        "single_parent_percentage": round(total_percentage, 2),
                        "single_father_percentage": round(fathers_percentage, 2),
                        "single_mother_percentage": round(mothers_percentage, 2)
                    })

                    # Additionner pour le calcul de la moyenne EPCI
                    total_households += commune_households
                    total_single_parent_families += commune_single_parent
                    total_single_fathers += commune_single_fathers
                    total_single_mothers += commune_single_mothers
                else:
                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": 0.0,
                        "single_parent_families": 0.0,
                        "single_fathers": 0.0,
                        "single_mothers": 0.0,
                        "single_parent_percentage": 0.0,
                        "single_father_percentage": 0.0,
                        "single_mother_percentage": 0.0
                    })

            # Calculer les moyennes pour l'EPCI
            epci_single_parent_percentage = (total_single_parent_families / total_households * 100) if total_households > 0 else 0
            epci_single_father_percentage = (total_single_fathers / total_single_parent_families * 100) if total_single_parent_families > 0 else 0
            epci_single_mother_percentage = (total_single_mothers / total_single_parent_families * 100) if total_single_parent_families > 0 else 0

            # Trier par pourcentage de familles monoparentales décroissant
            communes_data.sort(key=lambda x: x["single_parent_percentage"], reverse=True)

            return {
                "epci": epci,
                "epci_name": epci_name,
                "year": latest_year,
                "communes_count": len(communes),
                "total_households": total_households,
                "total_single_parent_families": total_single_parent_families,
                "total_single_fathers": total_single_fathers,
                "total_single_mothers": total_single_mothers,
                "epci_single_parent_percentage": round(epci_single_parent_percentage, 2),
                "epci_single_father_percentage": round(epci_single_father_percentage, 2),
                "epci_single_mother_percentage": round(epci_single_mother_percentage, 2),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des données des familles monoparentales pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Retourner une structure valide avec des valeurs par défaut
            return {
                "epci": epci,
                "epci_name": "",
                "year": 2021,
                "communes_count": 0,
                "total_households": 0.0,
                "total_single_parent_families": 0.0,
                "total_single_fathers": 0.0,
                "total_single_mothers": 0.0,
                "epci_single_parent_percentage": 0.0,
                "epci_single_father_percentage": 0.0,
                "epci_single_mother_percentage": 0.0,
                "communes": []
            }
        finally:
            db.close()

    def get_large_families_by_epci(self, epci: str):
        """Récupère les statistiques des familles nombreuses pour toutes les communes d'un EPCI"""
        try:
            # Établir une connexion à la base de données
            db = SessionLocal()

            # Récupérer les communes de l'EPCI
            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "year": 2021,  # Valeur par défaut
                    "communes_count": 0,
                    "total_households": 0.0,
                    "total_large_families": 0.0,
                    "total_families_3_children": 0.0,
                    "total_families_4_plus_children": 0.0,
                    "epci_large_families_percentage": 0.0,
                    "communes": []
                }

            # Récupérer le nom de l'EPCI
            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # Récupérer l'année la plus récente disponible
            latest_year = db.query(func.max(Family.year)).scalar() or 2021

            # Récupérer les données pour chaque commune
            communes_data = []
            total_households = 0
            total_large_families = 0
            total_families_3_children = 0
            total_families_4_plus_children = 0

            for code, name in communes:
                # Récupérer les données familiales pour cette commune et l'année la plus récente
                commune_data = db.query(Family).filter(
                    Family.geo_code == code,
                    Family.year == latest_year
                ).first()

                if commune_data:
                    # Récupérer les valeurs en sécurisant les None
                    commune_households = self._safe_float(commune_data.total_households)
                    commune_3_children = self._safe_float(commune_data.children_under_24_three_siblings)
                    commune_4_plus_children = self._safe_float(commune_data.children_under_24_four_or_more_siblings)

                    # Calculer le total des familles nombreuses (3 enfants ou plus)
                    commune_large_families = commune_3_children + commune_4_plus_children

                    # Calculer les pourcentages
                    large_families_percentage = (commune_large_families / commune_households * 100) if commune_households > 0 else 0
                    families_3_children_percentage = (commune_3_children / commune_households * 100) if commune_households > 0 else 0
                    families_4_plus_percentage = (commune_4_plus_children / commune_households * 100) if commune_households > 0 else 0

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": commune_households,
                        "large_families": commune_large_families,
                        "families_3_children": commune_3_children,
                        "families_4_plus_children": commune_4_plus_children,
                        "large_families_percentage": round(large_families_percentage, 2),
                        "families_3_children_percentage": round(families_3_children_percentage, 2),
                        "families_4_plus_percentage": round(families_4_plus_percentage, 2)
                    })

                    # Additionner pour le calcul de la moyenne EPCI
                    total_households += commune_households
                    total_large_families += commune_large_families
                    total_families_3_children += commune_3_children
                    total_families_4_plus_children += commune_4_plus_children
                else:
                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": 0.0,
                        "large_families": 0.0,
                        "families_3_children": 0.0,
                        "families_4_plus_children": 0.0,
                        "large_families_percentage": 0.0,
                        "families_3_children_percentage": 0.0,
                        "families_4_plus_percentage": 0.0
                    })

            # Calculer les moyennes pour l'EPCI
            epci_large_families_percentage = (total_large_families / total_households * 100) if total_households > 0 else 0
            epci_families_3_children_percentage = (total_families_3_children / total_households * 100) if total_households > 0 else 0
            epci_families_4_plus_percentage = (total_families_4_plus_children / total_households * 100) if total_households > 0 else 0

            # Trier par pourcentage de familles nombreuses décroissant
            communes_data.sort(key=lambda x: x["large_families_percentage"], reverse=True)

            return {
                "epci": epci,
                "epci_name": epci_name,
                "year": latest_year,
                "communes_count": len(communes),
                "total_households": total_households,
                "total_large_families": total_large_families,
                "total_families_3_children": total_families_3_children,
                "total_families_4_plus_children": total_families_4_plus_children,
                "epci_large_families_percentage": round(epci_large_families_percentage, 2),
                "epci_families_3_children_percentage": round(epci_families_3_children_percentage, 2),
                "epci_families_4_plus_percentage": round(epci_families_4_plus_percentage, 2),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des données des familles nombreuses pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # Retourner une structure valide avec des valeurs par défaut
            return {
                "epci": epci,
                "epci_name": "",
                "year": 2021,
                "communes_count": 0,
                "total_households": 0.0,
                "total_large_families": 0.0,
                "total_families_3_children": 0.0,
                "total_families_4_plus_children": 0.0,
                "epci_large_families_percentage": 0.0,
                "epci_families_3_children_percentage": 0.0,
                "epci_families_4_plus_percentage": 0.0,
                "communes": []
            }
        finally:
            db.close()
