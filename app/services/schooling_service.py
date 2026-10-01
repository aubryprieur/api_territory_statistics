from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
from app.models import SchoolingSummary, GeoCode


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
            if float_val in [float('inf'), float('-inf')] or float_val != float_val:
                return 0.0
            return float_val
        except (TypeError, ValueError):
            return 0.0

    # =========================================================================
    # Lecture depuis schooling_summary (pré-agrégée par commune et année)
    # Mêmes sommes et mêmes formules que les anciennes requêtes sur `schooling`,
    # mais sur ~35 000 lignes/an au lieu de plusieurs millions.
    # =========================================================================
    YEARS = range(2017, 2022)

    def _format_rates(self, row):
        """Construit le dict de taux à partir d'une ligne agrégée (ou zéros si absente)."""
        total_2y = self._safe_float(row.total_2y) if row else 0.0
        schooled_2y = self._safe_float(row.schooled_2y) if row else 0.0
        total_3_5y = self._safe_float(row.total_3_5y) if row else 0.0
        schooled_3_5y = self._safe_float(row.schooled_3_5y) if row else 0.0
        return {
            "total_children_2y": total_2y,
            "schooled_children_2y": schooled_2y,
            "schooling_rate_2y": round((schooled_2y / total_2y * 100) if total_2y > 0 else 0, 1),
            "total_children_3_5y": total_3_5y,
            "schooled_children_3_5y": schooled_3_5y,
            "schooling_rate_3_5y": round((schooled_3_5y / total_3_5y * 100) if total_3_5y > 0 else 0, 1)
        }

    def _rates_by_year(self, geo_filter=None, communes=None):
        """
        Taux par année en UNE requête (GROUP BY year) sur schooling_summary.

        Args:
            geo_filter: tuple (colonne GeoCode, valeur) → JOIN geo_codes (département, région)
            communes: liste de codes communes (commune, EPCI)
            aucun des deux → France entière
        """
        query = self.db.query(
            SchoolingSummary.year,
            func.sum(SchoolingSummary.total_2y).label('total_2y'),
            func.sum(SchoolingSummary.schooled_2y).label('schooled_2y'),
            func.sum(SchoolingSummary.total_3_5y).label('total_3_5y'),
            func.sum(SchoolingSummary.schooled_3_5y).label('schooled_3_5y'),
        ).filter(SchoolingSummary.year.in_(list(self.YEARS)))

        if geo_filter:
            column, value = geo_filter
            query = query.join(
                GeoCode, SchoolingSummary.geo_code == GeoCode.codgeo
            ).filter(column == str(value))
        elif communes:
            query = query.filter(SchoolingSummary.geo_code.in_(communes))

        rows = {row.year: row for row in query.group_by(SchoolingSummary.year).all()}
        return {year: self._format_rates(rows.get(year)) for year in self.YEARS}

    # =========================================================================
    # Commune (inchangé)
    # =========================================================================
    def get_commune_schooling(self, commune: str):
        """Récupère les données de scolarisation pour une commune"""
        try:
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
            results = self._rates_by_year(communes=[commune])

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

    # =========================================================================
    # EPCI (inchangé)
    # =========================================================================
    def get_epci_schooling(self, epci: str):
        """Récupère les données de scolarisation pour un EPCI"""
        try:
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {"territory_type": "epci", "code": epci, "name": "EPCI inconnu", "data": {}}

            communes = [c[0] for c in communes]

            results = self._rates_by_year(communes=communes)

            return {"territory_type": "epci", "code": epci, "name": f"EPCI {epci}", "data": results}
        except SQLAlchemyError as e:
            print(f"Erreur pour l'EPCI {epci}: {str(e)}")
            return {"territory_type": "epci", "code": epci, "name": "Erreur", "data": {}}
        finally:
            self.close()

    # =========================================================================
    # Département — OPTIMISÉ : 5 requêtes JOIN (1/partition) au lieu de 10 IN
    # =========================================================================
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

            print(f"\nNombre de communes trouvées pour le département {dep}: {len(communes)}")

            # OPTIMISATION : 1 requête par année avec JOIN au lieu de 2 avec IN(...)
            results = self._rates_by_year(geo_filter=(GeoCode.dep, dep))

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

    # =========================================================================
    # Région — OPTIMISÉ : 5 requêtes JOIN (1/partition) au lieu de 10 IN
    # =========================================================================
    def get_region_schooling(self, reg: str):
        """Récupère les données de scolarisation pour une région"""
        try:
            region_check = self.db.query(GeoCode.reg).filter(GeoCode.reg == str(reg)).first()
            if not region_check:
                return {"territory_type": "region", "code": reg, "name": "Région inconnue", "data": {}}

            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == str(reg)).all()

            if not communes:
                return {"territory_type": "region", "code": reg, "name": "Région inconnue", "data": {}}

            # OPTIMISATION : 1 requête par année avec JOIN au lieu de 2 avec IN(...)
            results = self._rates_by_year(geo_filter=(GeoCode.reg, reg))

            return {"territory_type": "region", "code": reg, "name": f"Région {reg}", "data": results}
        except SQLAlchemyError as e:
            print(f"Erreur pour la région {reg}: {str(e)}")
            return {"territory_type": "region", "code": reg, "name": "Erreur", "data": {}}
        finally:
            self.close()

    # =========================================================================
    # France — OPTIMISÉ : 5 requêtes (1/partition) au lieu de 10
    # =========================================================================
    def get_france_schooling(self):
        """Récupère les données de scolarisation pour toute la France"""
        try:
            # OPTIMISATION : 1 requête par année (pas de filtre géo, pas de JOIN)
            results = self._rates_by_year()

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

    # =========================================================================
    # EPCI — liste des communes avec statistiques (inchangé)
    # =========================================================================
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
            latest_year = 2021

            for code, name in communes:
                commune_data = self.get_commune_schooling(code)

                if commune_data and "data" in commune_data and commune_data["data"]:
                    years = sorted(commune_data["data"].keys())
                    if years:
                        latest_year = years[-1]
                        year_data = commune_data["data"][latest_year]
                        communes_data.append({
                            "code": code,
                            "name": name,
                            "schooling_rate_2y": year_data.get("schooling_rate_2y", 0),
                            "total_children_2y": year_data.get("total_children_2y", 0),
                            "schooled_children_2y": year_data.get("schooled_children_2y", 0),
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
