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

    # =========================================================================
    # OPTIMISATION : agrégation SQL directe au lieu de charger tous les objets
    # =========================================================================
    def _aggregate_families_sql(self, geo_filter=None, commune_codes=None, start_year=None, end_year=None):
        """
        Agrège les données familles directement en SQL avec GROUP BY year.
        Remplace _format_response pour les gros volumes (département, région, France).

        Args:
            geo_filter: tuple (column, value) pour JOIN sur geo_codes
            commune_codes: liste de codes communes (pour EPCI)
            start_year, end_year: filtres d'années pour l'évolution
        """
        query = self.db.query(
            Family.year,
            func.sum(Family.total_households).label('total_households'),
            func.sum(Family.couples_with_children).label('couples_with_children'),
            func.sum(Family.single_parent_families).label('single_parent_families'),
            func.sum(Family.single_fathers).label('single_fathers'),
            func.sum(Family.single_mothers).label('single_mothers'),
            func.sum(Family.couples_without_children).label('couples_without_children'),
            func.sum(Family.children_under_24_three_siblings).label('children_3'),
            func.sum(Family.children_under_24_four_or_more_siblings).label('children_4p'),
        )

        # Appliquer le filtre géographique
        if geo_filter:
            column, value = geo_filter
            query = query.join(
                GeoCode, Family.geo_code == GeoCode.codgeo
            ).filter(column == str(value))
        elif commune_codes is not None:
            query = query.filter(Family.geo_code.in_(commune_codes))

        query = query.group_by(Family.year)
        rows = query.all()

        # Construire data_by_year dans le même format que _format_response
        data_by_year = {}
        for row in rows:
            total_families = self._safe_float(row.total_households)
            couples_with_children = self._safe_float(row.couples_with_children)
            single_parent_families = self._safe_float(row.single_parent_families)
            single_fathers = self._safe_float(row.single_fathers)
            single_mothers = self._safe_float(row.single_mothers)
            couples_without_children = self._safe_float(row.couples_without_children)
            families_with_3_children = self._safe_float(row.children_3)
            families_with_4_plus_children = self._safe_float(row.children_4p)
            total_large_families = families_with_3_children + families_with_4_plus_children

            data = {
                "total_families": total_families,
                "couples_with_children": couples_with_children,
                "single_parent_families": single_parent_families,
                "single_fathers": single_fathers,
                "single_mothers": single_mothers,
                "couples_without_children": couples_without_children,
                "families_with_3_children": families_with_3_children,
                "families_with_4_plus_children": families_with_4_plus_children,
                "total_large_families": total_large_families,
            }

            # Calculer les pourcentages
            if total_families > 0:
                data["large_families_percentage"] = round(
                    (total_large_families / total_families) * 100, 2
                )
                data["couples_with_children_percentage"] = round(
                    (couples_with_children / total_families) * 100, 2
                )
                data["single_parent_families_percentage"] = round(
                    (single_parent_families / total_families) * 100, 2
                )
                data["couples_without_children_percentage"] = round(
                    (couples_without_children / total_families) * 100, 2
                )

            data_by_year[row.year] = data

        # Calcul des évolutions
        evolution = self._calculate_evolution(data_by_year, start_year, end_year)

        return {
            "family_data": data_by_year,
            "evolution": evolution
        }

    # =========================================================================
    # Commune (inchangé — peu de lignes)
    # =========================================================================
    def get_families_by_commune(self, geo_code: str, start_year: int = None, end_year: int = None):
        """ Récupère les données des familles pour une commune donnée """
        try:
            results = self.db.query(Family).filter(Family.geo_code == geo_code).all()
            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            self.close()

    # =========================================================================
    # EPCI (inchangé — peu de communes)
    # =========================================================================
    def get_families_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées par EPCI """
        try:
            db = SessionLocal()

            communes = [geo.codgeo for geo in db.query(GeoCode).filter(GeoCode.epci == epci).all()]
            if not communes:
                return {"error": "Aucune commune trouvée pour cet EPCI"}

            results = db.query(Family).filter(Family.geo_code.in_(communes)).all()

            return self._format_response(results, start_year, end_year)
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    # =========================================================================
    # Département — OPTIMISÉ : SQL GROUP BY + JOIN au lieu de IN(...)
    # =========================================================================
    def get_families_by_department(self, dep: str, start_year: int = None, end_year: int = None):
        """Récupère les données agrégées par département"""
        try:
            normalized_dep = dep.zfill(2)

            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.dep == normalized_dep).all()
            if not communes:
                return {"error": f"Aucune commune trouvée pour ce département {dep}"}

            # OPTIMISATION : agrégation SQL directe
            return self._aggregate_families_sql(
                geo_filter=(GeoCode.dep, normalized_dep),
                start_year=start_year,
                end_year=end_year
            )
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            self.close()

    # =========================================================================
    # Région — OPTIMISÉ : SQL GROUP BY + JOIN au lieu de IN(...)
    # =========================================================================
    def get_families_by_region(self, reg: str, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées par région """
        try:
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == str(reg)).all()
            if not communes:
                return {"error": "Aucune commune trouvée pour cette région"}

            # OPTIMISATION : agrégation SQL directe
            return self._aggregate_families_sql(
                geo_filter=(GeoCode.reg, reg),
                start_year=start_year,
                end_year=end_year
            )
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            self.close()

    # =========================================================================
    # France — OPTIMISÉ : SQL GROUP BY au lieu de charger ~175k lignes
    # =========================================================================
    def get_families_france(self, start_year: int = None, end_year: int = None):
        """ Récupère les données agrégées pour toute la France """
        try:
            # OPTIMISATION : agrégation SQL directe (pas de filtre géo)
            return self._aggregate_families_sql(
                start_year=start_year,
                end_year=end_year
            )
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            self.close()

    # =========================================================================
    # _format_response (inchangé — utilisé pour commune et EPCI)
    # =========================================================================
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
                data["large_families_percentage"] = round(
                    (data["total_large_families"] / total_families) * 100, 2
                )
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

    # =========================================================================
    # _calculate_evolution (inchangé)
    # =========================================================================
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

    # =========================================================================
    # EPCI détails communes (inchangés)
    # =========================================================================
    def get_couples_with_children_by_epci(self, epci: str):
        """Récupère les statistiques des couples avec enfants pour toutes les communes d'un EPCI"""
        try:
            db = SessionLocal()

            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "year": 2021,
                    "communes_count": 0,
                    "total_households": 0.0,
                    "total_couples_with_children": 0.0,
                    "epci_couples_with_children_percentage": 0.0,
                    "communes": []
                }

            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            latest_year = db.query(func.max(Family.year)).scalar() or 2021

            communes_data = []
            total_households = 0
            total_couples_with_children = 0

            for code, name in communes:
                commune_data = db.query(Family).filter(
                    Family.geo_code == code,
                    Family.year == latest_year
                ).first()

                if commune_data:
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

            epci_percentage = (total_couples_with_children / total_households * 100) if total_households > 0 else 0

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
            return {
                "epci": epci,
                "epci_name": "",
                "year": 2021,
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
            db = SessionLocal()

            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
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

            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            latest_year = db.query(func.max(Family.year)).scalar() or 2021

            communes_data = []
            total_households = 0
            total_single_parent = 0
            total_single_fathers = 0
            total_single_mothers = 0

            for code, name in communes:
                commune_data = db.query(Family).filter(
                    Family.geo_code == code,
                    Family.year == latest_year
                ).first()

                if commune_data:
                    commune_households = self._safe_float(commune_data.total_households)
                    commune_single_parent = self._safe_float(commune_data.single_parent_families)
                    commune_single_fathers = self._safe_float(commune_data.single_fathers)
                    commune_single_mothers = self._safe_float(commune_data.single_mothers)

                    percentage = (commune_single_parent / commune_households * 100) if commune_households > 0 else 0
                    father_pct = (commune_single_fathers / commune_single_parent * 100) if commune_single_parent > 0 else 0
                    mother_pct = (commune_single_mothers / commune_single_parent * 100) if commune_single_parent > 0 else 0

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": commune_households,
                        "single_parent_families": commune_single_parent,
                        "single_fathers": commune_single_fathers,
                        "single_mothers": commune_single_mothers,
                        "single_parent_percentage": round(percentage, 2),
                        "single_father_percentage": round(father_pct, 2),
                        "single_mother_percentage": round(mother_pct, 2)
                    })

                    total_households += commune_households
                    total_single_parent += commune_single_parent
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

            epci_pct = (total_single_parent / total_households * 100) if total_households > 0 else 0
            epci_father_pct = (total_single_fathers / total_single_parent * 100) if total_single_parent > 0 else 0
            epci_mother_pct = (total_single_mothers / total_single_parent * 100) if total_single_parent > 0 else 0

            communes_data.sort(key=lambda x: x["single_parent_percentage"], reverse=True)

            return {
                "epci": epci,
                "epci_name": epci_name,
                "year": latest_year,
                "communes_count": len(communes),
                "total_households": total_households,
                "total_single_parent_families": total_single_parent,
                "total_single_fathers": total_single_fathers,
                "total_single_mothers": total_single_mothers,
                "epci_single_parent_percentage": round(epci_pct, 2),
                "epci_single_father_percentage": round(epci_father_pct, 2),
                "epci_single_mother_percentage": round(epci_mother_pct, 2),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des familles monoparentales pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
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
            db = SessionLocal()

            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
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

            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            latest_year = db.query(func.max(Family.year)).scalar() or 2021

            communes_data = []
            total_households = 0
            total_large_families = 0
            total_3_children = 0
            total_4_plus = 0

            for code, name in communes:
                commune_data = db.query(Family).filter(
                    Family.geo_code == code,
                    Family.year == latest_year
                ).first()

                if commune_data:
                    commune_households = self._safe_float(commune_data.total_households)
                    commune_3 = self._safe_float(commune_data.children_under_24_three_siblings)
                    commune_4p = self._safe_float(commune_data.children_under_24_four_or_more_siblings)
                    commune_large = commune_3 + commune_4p

                    large_pct = (commune_large / commune_households * 100) if commune_households > 0 else 0
                    pct_3 = (commune_3 / commune_households * 100) if commune_households > 0 else 0
                    pct_4p = (commune_4p / commune_households * 100) if commune_households > 0 else 0

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_households": commune_households,
                        "large_families": commune_large,
                        "families_3_children": commune_3,
                        "families_4_plus_children": commune_4p,
                        "large_families_percentage": round(large_pct, 2),
                        "families_3_children_percentage": round(pct_3, 2),
                        "families_4_plus_percentage": round(pct_4p, 2)
                    })

                    total_households += commune_households
                    total_large_families += commune_large
                    total_3_children += commune_3
                    total_4_plus += commune_4p
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

            epci_large_pct = (total_large_families / total_households * 100) if total_households > 0 else 0
            epci_3_pct = (total_3_children / total_households * 100) if total_households > 0 else 0
            epci_4p_pct = (total_4_plus / total_households * 100) if total_households > 0 else 0

            communes_data.sort(key=lambda x: x["large_families_percentage"], reverse=True)

            return {
                "epci": epci,
                "epci_name": epci_name,
                "year": latest_year,
                "communes_count": len(communes),
                "total_households": total_households,
                "total_large_families": total_large_families,
                "total_families_3_children": total_3_children,
                "total_families_4_plus_children": total_4_plus,
                "epci_large_families_percentage": round(epci_large_pct, 2),
                "epci_families_3_children_percentage": round(epci_3_pct, 2),
                "epci_families_4_plus_percentage": round(epci_4p_pct, 2),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des familles nombreuses pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
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
