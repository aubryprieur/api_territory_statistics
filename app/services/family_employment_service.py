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

    def _adjust_age_group_format(self, age_group):
        """Ajuste le format du groupe d'âge pour qu'il corresponde au format de la base de données"""
        if age_group == "0":
            return "00"
        elif age_group == "3":
            return "03"
        return age_group

    def get_available_years(self):
        """Récupère les années disponibles dans la base de données"""
        try:
            years = self.db.query(FamilyEmployment.year).distinct().order_by(FamilyEmployment.year).all()
            return [year[0] for year in years]
        except Exception as e:
            print(f"Erreur lors de la récupération des années disponibles: {str(e)}")
            return [2021]
        finally:
            self.close()

    # =========================================================================
    # Méthode d'origine (inchangée — pour commune, EPCI, détails communes)
    # =========================================================================
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
                "age_group": "0-2 ans" if age_group in ["0", "00"] else "3-5 ans"
            }
        except Exception as e:
            print(f"Erreur dans le calcul de la distribution: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "total_count": 0,
                "distributions": {},
                "age_group": "0-2 ans" if age_group in ["0", "00"] else "3-5 ans"
            }

    # =========================================================================
    # OPTIMISÉ : agrégation SQL GROUP BY tf12 au lieu de charger toutes les lignes
    # Retourne exactement le même format que _calculate_distribution
    # =========================================================================
    def _calculate_distribution_sql(self, age_group="0", year=2021, geo_filter=None):
        """
        Calcule la distribution directement en SQL avec GROUP BY tf12.

        Args:
            age_group: groupe d'âge ("0" ou "3")
            year: année
            geo_filter: tuple (column, value) pour JOIN sur geo_codes, ou None pour France
        """
        try:
            formatted_age_group = self._adjust_age_group_format(age_group)

            # 1 requête SQL avec GROUP BY tf12 au lieu de charger toutes les lignes
            query = self.db.query(
                FamilyEmployment.tf12,
                func.sum(FamilyEmployment.number).label('count')
            ).filter(
                FamilyEmployment.age_group == formatted_age_group,
                FamilyEmployment.year == year
            )

            # Appliquer le filtre géographique via JOIN si nécessaire
            if geo_filter:
                column, value = geo_filter
                query = query.join(
                    GeoCode, FamilyEmployment.geo_code == GeoCode.codgeo
                ).filter(column == str(value))

            query = query.group_by(FamilyEmployment.tf12)
            rows = query.all()

            # Construire le résultat dans le même format que _calculate_distribution
            total = sum(float(row.count or 0) for row in rows)

            distributions = {}
            if total > 0:
                for row in sorted(rows, key=lambda r: r.tf12):
                    count = float(row.count or 0)
                    percentage = (count / total * 100) if total > 0 else 0

                    key = self.tf12_labels.get(row.tf12, f"Type {row.tf12}")
                    distributions[key] = {
                        "code": str(row.tf12),
                        "count": count,
                        "percentage": round(percentage, 1)
                    }

            return {
                "total_count": float(total),
                "distributions": distributions,
                "age_group": "0-2 ans" if age_group in ["0", "00"] else "3-5 ans"
            }
        except Exception as e:
            print(f"Erreur dans _calculate_distribution_sql: {str(e)}")
            return {
                "total_count": 0,
                "distributions": {},
                "age_group": "0-2 ans" if age_group in ["0", "00"] else "3-5 ans"
            }

    # =========================================================================
    # Commune (inchangé)
    # =========================================================================
    def get_commune_distribution(self, code: str, age_group="0", year=None):
        """Récupère la distribution pour une commune"""
        try:
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            geo_info = self.db.query(GeoCode).filter(GeoCode.codgeo == str(code)).first()
            if not geo_info:
                return {
                    "territory_type": "commune",
                    "code": code,
                    "name": "Commune inconnue",
                    "data": {}
                }

            results = {}

            formatted_age_group = self._adjust_age_group_format(age_group)

            print(f"Recherche des données pour commune {code}, année {year}, groupe d'âge {formatted_age_group}")

            commune_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.geo_code == str(code),
                FamilyEmployment.age_group == formatted_age_group,
                FamilyEmployment.year == year
            ).all()

            if commune_data:
                results[year] = self._calculate_distribution(commune_data, age_group)
                print(f"Données trouvées : {len(commune_data)} enregistrements")
            else:
                print(f"Aucune donnée trouvée pour la commune {code}, année {year}, groupe d'âge {formatted_age_group}")

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

    # =========================================================================
    # EPCI (inchangé)
    # =========================================================================
    def get_epci_distribution(self, epci: str, age_group="0", year=None):
        """Récupère la distribution pour un EPCI"""
        try:
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

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

            formatted_age_group = self._adjust_age_group_format(age_group)

            epci_data = self.db.query(FamilyEmployment).filter(
                FamilyEmployment.geo_code.in_(commune_codes),
                FamilyEmployment.age_group == formatted_age_group,
                FamilyEmployment.year == year
            ).all()

            if epci_data:
                results[year] = self._calculate_distribution(epci_data, age_group)

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

    # =========================================================================
    # Département — OPTIMISÉ : SQL GROUP BY + JOIN au lieu de IN(...)
    # =========================================================================
    def get_department_distribution(self, dep: str, age_group="0", year=None):
        """Récupère la distribution pour un département"""
        try:
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.dep == str(dep)).all()
            if not communes:
                return {
                    "territory_type": "department",
                    "code": dep,
                    "name": "Département inconnu",
                    "data": {}
                }

            results = {}

            # OPTIMISATION : SQL GROUP BY + JOIN au lieu de charger toutes les lignes
            distribution = self._calculate_distribution_sql(
                age_group=age_group,
                year=year,
                geo_filter=(GeoCode.dep, dep)
            )

            if distribution["total_count"] > 0:
                results[year] = distribution

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

    # =========================================================================
    # Région — OPTIMISÉ : SQL GROUP BY + JOIN au lieu de IN(...)
    # =========================================================================
    def get_region_distribution(self, reg: str, age_group="0", year=None):
        """Récupère la distribution pour une région"""
        try:
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.reg == str(reg)).all()
            if not communes:
                return {
                    "territory_type": "region",
                    "code": reg,
                    "name": "Région inconnue",
                    "data": {}
                }

            results = {}

            # OPTIMISATION : SQL GROUP BY + JOIN au lieu de charger toutes les lignes
            distribution = self._calculate_distribution_sql(
                age_group=age_group,
                year=year,
                geo_filter=(GeoCode.reg, reg)
            )

            if distribution["total_count"] > 0:
                results[year] = distribution

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

    # =========================================================================
    # France — OPTIMISÉ : SQL GROUP BY au lieu de charger ~35k × 8 lignes
    # =========================================================================
    def get_france_distribution(self, age_group="0", year=None):
        """Récupère la distribution pour la France entière"""
        try:
            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            results = {}

            # OPTIMISATION : SQL GROUP BY sans filtre géo (pas de JOIN)
            distribution = self._calculate_distribution_sql(
                age_group=age_group,
                year=year
            )

            if distribution["total_count"] > 0:
                results[year] = distribution

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

    # =========================================================================
    # EPCI — détails communes (inchangé)
    # =========================================================================
    def get_communes_distribution_by_epci(self, epci: str, age_group="0", year=None):
        """Récupère la distribution pour toutes les communes d'un EPCI"""
        try:
            db = SessionLocal()

            if year is None:
                available_years = self.get_available_years()
                year = available_years[-1] if available_years else 2021

            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()
            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "year": year,
                    "communes_count": 0,
                    "communes": []
                }

            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            formatted_age_group = self._adjust_age_group_format(age_group)

            communes_data = []
            total_families = 0
            total_dual_active = 0
            total_single_parent_active = 0

            for code, name in communes:
                commune_data = db.query(FamilyEmployment).filter(
                    FamilyEmployment.geo_code == code,
                    FamilyEmployment.age_group == formatted_age_group,
                    FamilyEmployment.year == year
                ).all()

                if commune_data:
                    distribution = self._calculate_distribution(commune_data, age_group)

                    total_count = distribution["total_count"]
                    distributions = distribution["distributions"]

                    dual_active_count = distributions.get("Couple avec enfant(s) - Deux parents actifs ayant un emploi", {}).get("count", 0)
                    dual_active_rate = (dual_active_count / total_count * 100) if total_count > 0 else 0

                    single_parent_active_count = (
                        distributions.get("Famille monoparentale - Homme actif ayant un emploi", {}).get("count", 0) +
                        distributions.get("Famille monoparentale - Femme active ayant un emploi", {}).get("count", 0)
                    )
                    single_parent_active_rate = (single_parent_active_count / total_count * 100) if total_count > 0 else 0

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_families": total_count,
                        "dual_active_count": dual_active_count,
                        "dual_active_rate": round(dual_active_rate, 1),
                        "single_parent_active_count": single_parent_active_count,
                        "single_parent_active_rate": round(single_parent_active_rate, 1),
                        "distributions": distributions
                    })

                    total_families += total_count
                    total_dual_active += dual_active_count
                    total_single_parent_active += single_parent_active_count
                else:
                    communes_data.append({
                        "code": code,
                        "name": name,
                        "total_families": 0,
                        "dual_active_count": 0,
                        "dual_active_rate": 0,
                        "single_parent_active_count": 0,
                        "single_parent_active_rate": 0,
                        "distributions": {}
                    })

            communes_data.sort(key=lambda x: x["dual_active_rate"], reverse=True)

            epci_dual_active_rate = (total_dual_active / total_families * 100) if total_families > 0 else 0
            epci_single_parent_active_rate = (total_single_parent_active / total_families * 100) if total_families > 0 else 0

            return {
                "epci": epci,
                "epci_name": epci_name,
                "year": year,
                "age_group": "0-2 ans" if age_group in ["0", "00"] else "3-5 ans",
                "communes_count": len(communes),
                "total_families": total_families,
                "total_dual_active": total_dual_active,
                "total_single_parent_active": total_single_parent_active,
                "epci_dual_active_rate": round(epci_dual_active_rate, 1),
                "epci_single_parent_active_rate": round(epci_single_parent_active_rate, 1),
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "epci": epci,
                "epci_name": "",
                "year": year or 2021,
                "age_group": "0-2 ans" if age_group in ["0", "00"] else "3-5 ans",
                "communes_count": 0,
                "total_families": 0,
                "total_dual_active": 0,
                "total_single_parent_active": 0,
                "epci_dual_active_rate": 0,
                "epci_single_parent_active_rate": 0,
                "communes": []
            }
        finally:
            db.close()
