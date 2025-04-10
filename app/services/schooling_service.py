from sqlalchemy import func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
from app.models import Schooling, GeoCode

class SchoolingService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        self.db.close()

    def _safe_float(self, value):
        """Convertit une valeur en float de manière sécurisée pour JSON"""
        try:
            if value is None:
                return 0.0
            float_val = float(value)
            if float_val in [float('inf'), float('-inf')] or float_val != float_val:  # Vérifie NaN et inf
                return 0.0
            return float_val
        except (TypeError, ValueError):
            return 0.0

    def _calculate_schooling_rates_optimized(self, year: int, communes: list = None):
        """Calcule les taux de scolarisation avec des agrégations SQL"""
        try:
            # Requête pour les enfants de 2 ans
            two_years_query = self.db.query(
                func.coalesce(func.sum(Schooling.number), 0).label('total'),
                func.coalesce(func.sum(
                    case(
                        (Schooling.education_status.in_(['1', '2', '3', '4', '5']), Schooling.number),
                        else_=0
                    )
                ), 0).label('schooled')
            ).filter(
                Schooling.year == year,
                Schooling.sex.in_(['1', '2']),
                Schooling.age == '002'  # Format correct à 3 caractères
            )

            if communes:
                two_years_query = two_years_query.filter(Schooling.geo_code.in_(communes))

            two_years = two_years_query.first()

            # Requête pour les enfants de 3-5 ans
            three_to_five_query = self.db.query(
                func.coalesce(func.sum(Schooling.number), 0).label('total'),
                func.coalesce(func.sum(
                    case(
                        (Schooling.education_status.in_(['1', '2', '3', '4', '5']), Schooling.number),
                        else_=0
                    )
                ), 0).label('schooled')
            ).filter(
                Schooling.year == year,
                Schooling.sex.in_(['1', '2']),
                Schooling.age.in_(['003', '004', '005'])  # Format correct
            )

            if communes:
                three_to_five_query = three_to_five_query.filter(Schooling.geo_code.in_(communes))

            three_to_five = three_to_five_query.first()

            # Sécurisation des valeurs
            total_2y = self._safe_float(two_years.total)
            schooled_2y = self._safe_float(two_years.schooled)
            rate_2y = (schooled_2y / total_2y * 100) if total_2y > 0 else 0

            total_3_5y = self._safe_float(three_to_five.total)
            schooled_3_5y = self._safe_float(three_to_five.schooled)
            rate_3_5y = (schooled_3_5y / total_3_5y * 100) if total_3_5y > 0 else 0

            return {
                "total_children_2y": total_2y,
                "schooled_children_2y": schooled_2y,
                "schooling_rate_2y": round(rate_2y, 1),
                "total_children_3_5y": total_3_5y,
                "schooled_children_3_5y": schooled_3_5y,
                "schooling_rate_3_5y": round(rate_3_5y, 1)
            }
        except Exception as e:
            print(f"Erreur dans le calcul des taux : {str(e)}")
            return {
                "total_children_2y": 0.0,
                "schooled_children_2y": 0.0,
                "schooling_rate_2y": 0.0,
                "total_children_3_5y": 0.0,
                "schooled_children_3_5y": 0.0,
                "schooling_rate_3_5y": 0.0
            }

    def get_commune_schooling(self, commune: str):
        """Récupère les données de scolarisation pour une commune"""
        try:
            # Vérifier si la commune existe
            commune_check = self.db.query(GeoCode.codgeo).filter(GeoCode.codgeo == str(commune)).first()
            if not commune_check:
                return {
                    "territory_type": "commune",
                    "code": commune,
                    "name": "Commune inconnue",
                    "data": {}
                }

            print(f"\nCommune trouvée: {commune}")

            # Calculer les taux pour chaque année
            results = {year: self._calculate_schooling_rates_optimized(year, [commune]) for year in range(2017, 2022)}

            return {
                "territory_type": "commune",
                "code": commune,
                "name": f"Commune {commune}",
                "data": results
            }
        except SQLAlchemyError as e:
            print(f"Erreur pour la commune {commune}: {str(e)}")
            return {
                "territory_type": "commune",
                "code": commune,
                "name": "Erreur",
                "data": {}
            }
        finally:
            self.close()

    def get_epci_schooling(self, epci: str):
          """Récupère les données de scolarisation pour un EPCI"""
          try:
              communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()

              if not communes:
                  return {"territory_type": "epci", "code": epci, "name": "EPCI inconnu", "data": {}}

              communes = [c[0] for c in communes]

              results = {year: self._calculate_schooling_rates_optimized(year, communes) for year in range(2017, 2022)}

              return {"territory_type": "epci", "code": epci, "name": f"EPCI {epci}", "data": results}
          except SQLAlchemyError as e:
              print(f"Erreur pour l'EPCI {epci}: {str(e)}")
              return {"territory_type": "epci", "code": epci, "name": "Erreur", "data": {}}
          finally:
              self.close()

    def get_department_schooling(self, dep: str):
        """Récupère les données de scolarisation pour un département"""
        try:
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.dep == str(dep)).all()

            if not communes:
                return {
                    "territory_type": "department",
                    "code": dep,
                    "name": "Département inconnu",
                    "data": {}
                }

            communes = [c[0] for c in communes]
            print(f"\nNombre de communes trouvées pour le département {dep}: {len(communes)}")

            results = {}
            for year in range(2017, 2022):
                results[year] = self._calculate_schooling_rates_optimized(year, communes)

            return {
                "territory_type": "department",
                "code": dep,
                "name": f"Département {dep}",
                "data": results
            }
        except SQLAlchemyError as e:
            print(f"Erreur pour le département {dep}: {str(e)}")
            return {
                "territory_type": "department",
                "code": dep,
                "name": "Erreur",
                "data": {}
            }
        finally:
            self.close()


    def get_region_schooling(self, reg: str):
        """Récupère les données de scolarisation pour une région"""
        try:
            # Vérifier le format du code région
            region_check = self.db.query(GeoCode.reg).filter(GeoCode.reg == str(reg)).first()
            if not region_check:
                return {"territory_type": "region", "code": reg, "name": "Région inconnue", "data": {}}

            actual_reg = region_check[0]
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == actual_reg).all()

            if not communes:
                return {"territory_type": "region", "code": reg, "name": "Région inconnue", "data": {}}

            communes = [c[0] for c in communes]

            # Calculer les taux pour chaque année
            results = {year: self._calculate_schooling_rates_optimized(year, communes) for year in range(2017, 2022)}

            return {"territory_type": "region", "code": reg, "name": f"Région {reg}", "data": results}
        except SQLAlchemyError as e:
            print(f"Erreur pour la région {reg}: {str(e)}")
            return {"territory_type": "region", "code": reg, "name": "Erreur", "data": {}}
        finally:
            self.close()

    def get_france_schooling(self):
          """Récupère les données de scolarisation pour toute la France"""
          try:
              results = {year: self._calculate_schooling_rates_optimized(year) for year in range(2017, 2022)}

              return {
                  "territory_type": "country",
                  "code": "FR",
                  "name": "France",
                  "data": results
              }
          except SQLAlchemyError as e:
              print(f"Erreur pour la France: {str(e)}")
              return {
                  "territory_type": "country",
                  "code": "FR",
                  "name": "Erreur",
                  "data": {}
              }
          finally:
              self.close()

    def get_communes_schooling_by_epci(self, epci: str):
      """Récupère les taux de scolarisation pour toutes les communes d'un EPCI"""
      try:
          # Récupérer les communes de l'EPCI
          communes = self.db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

          if not communes:
              return {
                  "epci": epci,
                  "epci_name": "",
                  "communes_count": 0,
                  "communes": []
              }

          # Récupérer le nom de l'EPCI
          epci_info = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
          epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

          # Récupérer les données pour chaque commune
          communes_data = []
          latest_year = 2021  # Année par défaut, à ajuster selon les données disponibles

          for code, name in communes:
              # Récupérer les données de scolarisation pour cette commune
              commune_data = self.get_commune_schooling(code)

              # Extraire les données de la dernière année disponible
              if commune_data and "data" in commune_data and commune_data["data"]:
                  years = sorted(commune_data["data"].keys())
                  if years:
                      latest_year = years[-1]  # Dernière année disponible
                      year_data = commune_data["data"][latest_year]
                      communes_data.append({
                          "code": code,
                          "name": name,
                          # Données pour les enfants de 2 ans
                          "schooling_rate_2y": year_data.get("schooling_rate_2y", 0),
                          "total_children_2y": year_data.get("total_children_2y", 0),
                          "schooled_children_2y": year_data.get("schooled_children_2y", 0),
                          # Données pour les enfants de 3 à 5 ans
                          "schooling_rate_3_5y": year_data.get("schooling_rate_3_5y", 0),
                          "total_children_3_5y": year_data.get("total_children_3_5y", 0),
                          "schooled_children_3_5y": year_data.get("schooled_children_3_5y", 0)
                      })
                  else:
                      communes_data.append({
                          "code": code,
                          "name": name,
                          "schooling_rate_2y": 0,
                          "total_children_2y": 0,
                          "schooled_children_2y": 0,
                          "schooling_rate_3_5y": 0,
                          "total_children_3_5y": 0,
                          "schooled_children_3_5y": 0
                      })
              else:
                  communes_data.append({
                      "code": code,
                      "name": name,
                      "schooling_rate_2y": 0,
                      "total_children_2y": 0,
                      "schooled_children_2y": 0,
                      "schooling_rate_3_5y": 0,
                      "total_children_3_5y": 0,
                      "schooled_children_3_5y": 0
                  })

          # Trier par taux de scolarisation des 2 ans décroissant
          communes_data.sort(key=lambda x: x["schooling_rate_2y"], reverse=True)

          # Calculer les moyennes EPCI
          total_children_2y = sum(commune["total_children_2y"] for commune in communes_data)
          schooled_children_2y = sum(commune["schooled_children_2y"] for commune in communes_data)
          avg_schooling_rate_2y = (schooled_children_2y / total_children_2y * 100) if total_children_2y > 0 else 0

          total_children_3_5y = sum(commune["total_children_3_5y"] for commune in communes_data)
          schooled_children_3_5y = sum(commune["schooled_children_3_5y"] for commune in communes_data)
          avg_schooling_rate_3_5y = (schooled_children_3_5y / total_children_3_5y * 100) if total_children_3_5y > 0 else 0

          return {
              "epci": epci,
              "epci_name": epci_name,
              "year": latest_year,
              "communes_count": len(communes),
              "average_schooling_rate_2y": round(avg_schooling_rate_2y, 1),
              "average_schooling_rate_3_5y": round(avg_schooling_rate_3_5y, 1),
              "communes": communes_data
          }
      except Exception as e:
          print(f"Erreur lors de la récupération des données de scolarisation pour l'EPCI {epci}: {str(e)}")
          import traceback
          print(traceback.format_exc())
          return {
              "epci": epci,
              "epci_name": "",
              "communes_count": 0,
              "communes": []
          }
      finally:
          self.close()
