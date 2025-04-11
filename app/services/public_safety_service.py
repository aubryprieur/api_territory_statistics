from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Optional
from app.database import SessionLocal
from app.models import PublicSafety, GeoCode, Population

class PublicSafetyService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def _format_safety_data(self, data) -> list:
        """Formate les données de sécurité pour l'API"""
        return [
            {
                "year": item.year,
                "indicator_class": item.indicator_class,
                "rate": float(item.rate)
            }
            for item in data
        ]

    def get_by_commune(self, code: str) -> Dict:
        """Récupère les données de sécurité pour une commune et ses territoires parents"""
        try:
            # Récupérer les informations géographiques
            geo_info = self.db.query(GeoCode).filter(GeoCode.codgeo == str(code)).first()

            if not geo_info:
                return {
                    "commune": {"code": code, "name": None, "data": []},
                    "department": {"code": "", "name": None, "data": []},
                    "region": {"code": "", "name": None, "data": []}
                }

            # Récupérer les données pour chaque niveau
            commune_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'commune',
                    PublicSafety.territory_code == str(code)
                )
            ).all()

            department_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'department',
                    PublicSafety.territory_code == str(geo_info.dep)
                )
            ).all()

            region_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'region',
                    PublicSafety.territory_code == str(geo_info.reg)
                )
            ).all()

            return {
                "commune": {
                    "code": code,
                    "name": geo_info.libgeo,
                    "data": self._format_safety_data(commune_data)
                },
                "department": {
                    "code": geo_info.dep,
                    "name": f"Département {geo_info.dep}",
                    "data": self._format_safety_data(department_data)
                },
                "region": {
                    "code": geo_info.reg,
                    "name": f"Région {geo_info.reg}",
                    "data": self._format_safety_data(region_data)
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_commune: {str(e)}")
            return {
                "commune": {"code": code, "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {"code": "", "name": None, "data": []}
            }
        finally:
            self.close()

    def get_by_department(self, dep: str) -> Dict:
        """Récupère les données de sécurité pour un département et sa région parente"""
        try:
            # Récupérer les informations géographiques
            geo_info = self.db.query(GeoCode).filter(GeoCode.dep == str(dep)).first()

            if not geo_info:
                return {
                    "commune": {"code": "", "name": None, "data": []},
                    "department": {"code": dep, "name": None, "data": []},
                    "region": {"code": "", "name": None, "data": []}
                }

            # Récupérer les données
            department_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'department',
                    PublicSafety.territory_code == str(dep)
                )
            ).all()

            region_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'region',
                    PublicSafety.territory_code == str(geo_info.reg)
                )
            ).all()

            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {
                    "code": dep,
                    "name": f"Département {dep}",
                    "data": self._format_safety_data(department_data)
                },
                "region": {
                    "code": geo_info.reg,
                    "name": f"Région {geo_info.reg}",
                    "data": self._format_safety_data(region_data)
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_department: {str(e)}")
            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": dep, "name": None, "data": []},
                "region": {"code": "", "name": None, "data": []}
            }
        finally:
            self.close()

    def get_by_region(self, reg: str) -> Dict:
        """Récupère les données de sécurité pour une région"""
        try:
            # Récupérer les données
            region_data = self.db.query(PublicSafety).filter(
                and_(
                    PublicSafety.territory_type == 'region',
                    PublicSafety.territory_code == str(reg)
                )
            ).all()

            if not region_data:
                return {
                    "commune": {"code": "", "name": None, "data": []},
                    "department": {"code": "", "name": None, "data": []},
                    "region": {"code": reg, "name": None, "data": []}
                }

            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {
                    "code": reg,
                    "name": f"Région {reg}",
                    "data": self._format_safety_data(region_data)
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_region: {str(e)}")
            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {"code": reg, "name": None, "data": []}
            }
        finally:
            self.close()

    def get_domestic_violence_by_epci(self, epci: str):
        """Récupère les données de violences intrafamiliales pour toutes les communes d'un EPCI"""
        try:
            # Récupérer les communes de l'EPCI
            communes = self.db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "communes_count": 0,
                    "communes": []
                }

            commune_codes = [c[0] for c in communes]

            # Récupérer le nom de l'EPCI
            epci_info = self.db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # DEBUGGING: Vérifier les types d'indicateurs disponibles pour ces communes
            sample_commune = commune_codes[0] if commune_codes else None
            if sample_commune:
                available_indicators = self.db.query(PublicSafety.indicator_class).filter(
                    PublicSafety.territory_type == 'commune',
                    PublicSafety.territory_code == sample_commune
                ).distinct().all()
                print(f"Indicateurs disponibles pour {sample_commune}: {[i[0] for i in available_indicators]}")

            # Récupérer les données pour chaque commune
            communes_data = []
            total_population = 0

            for code in commune_codes:
                # Récupérer les informations géographiques de la commune
                geo_info = self.db.query(GeoCode).filter(GeoCode.codgeo == str(code)).first()

                if not geo_info:
                    continue

                # Récupérer les données de sécurité liées aux violences intrafamiliales
                # Utiliser ILIKE pour une recherche insensible à la casse
                commune_data = self.db.query(PublicSafety).filter(
                    and_(
                        PublicSafety.territory_type == 'commune',
                        PublicSafety.territory_code == str(code),
                        PublicSafety.indicator_class.ilike('%famili%')  # Recherche plus flexible
                    )
                ).order_by(PublicSafety.year).all()

                # Si aucune donnée trouvée, essayer une recherche encore plus large
                if not commune_data:
                    commune_data = self.db.query(PublicSafety).filter(
                        and_(
                            PublicSafety.territory_type == 'commune',
                            PublicSafety.territory_code == str(code),
                            or_(
                                PublicSafety.indicator_class.ilike('%violen%famili%'),
                                PublicSafety.indicator_class.ilike('%violen%intraf%'),
                                PublicSafety.indicator_class.ilike('%violen%conjug%')
                            )
                        )
                    ).order_by(PublicSafety.year).all()

                # DEBUGGING pour une commune qui devrait avoir des données
                if code == commune_codes[0]:  # Juste pour la première commune
                    all_data = self.db.query(PublicSafety).filter(
                        PublicSafety.territory_type == 'commune',
                        PublicSafety.territory_code == str(code)
                    ).all()
                    print(f"Classes d'indicateurs pour {code}: {set(d.indicator_class for d in all_data)}")
                    print(f"Données trouvées pour {code}: {len(commune_data)} enregistrements")

                # Récupérer la population
                pop_query = self.db.query(func.sum(Population.nb)).filter(Population.codgeo == str(code))
                population = pop_query.scalar() or 0
                total_population += population

                # Formater les données de sécurité par année
                yearly_data = []
                for item in commune_data:
                    yearly_data.append({
                        "year": item.year,
                        "rate": float(item.rate),
                        "indicator_class": item.indicator_class  # Ajouter pour débogage
                    })

                # Calculer le taux moyen si des données sont disponibles
                avg_rate = sum(item["rate"] for item in yearly_data) / len(yearly_data) if yearly_data else 0

                communes_data.append({
                    "code": code,
                    "name": geo_info.libgeo,
                    "population": population,
                    "average_rate": round(avg_rate, 2),
                    "yearly_data": yearly_data
                })

            # Trier les communes par taux moyen décroissant
            communes_data.sort(key=lambda x: x["average_rate"], reverse=True)

            # Calculer le taux moyen pour l'EPCI
            all_rates = [item["rate"] for commune in communes_data for item in commune["yearly_data"]]
            epci_avg_rate = sum(all_rates) / len(all_rates) if all_rates else 0

            return {
                "epci": epci,
                "epci_name": epci_name,
                "communes_count": len(communes_data),
                "total_population": total_population,
                "epci_average_rate": round(epci_avg_rate, 2),
                "communes": communes_data
            }

        except Exception as e:
            print(f"Erreur lors de la récupération des données de violences intrafamiliales pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "epci": epci,
                "epci_name": "",
                "communes_count": 0,
                "total_population": 0,
                "epci_average_rate": 0,
                "communes": []
            }
        finally:
            self.close()
