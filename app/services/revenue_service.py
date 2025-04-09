from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional, List
from app.database import SessionLocal
from app.models import Revenue, GeoCode

class RevenueService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def get_median_revenues(self, codgeo: str):
        """Récupère les revenus médians pour une commune"""
        try:
            results = self.db.query(Revenue).filter(
                Revenue.geo_type == 'commune',
                Revenue.geo_code == codgeo
            ).order_by(Revenue.year).all()

            medians = {}
            poverty_rates = {}
            for record in results:
                medians[record.year] = record.median_revenue
                poverty_rates[record.year] = record.poverty_rate

            return {
                "commune": codgeo,
                "median_revenues": medians,
                "poverty_rates": poverty_rates
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des revenus pour {codgeo}: {str(e)}")
            return {
                "commune": codgeo,
                "median_revenues": {},
                "poverty_rates": {}
            }
        finally:
            self.close()

    def get_median_revenues_epci(self, epci: str):
        """Récupère les revenus médians pour un EPCI"""
        try:
            results = self.db.query(Revenue).filter(
                Revenue.geo_type == 'epci',
                Revenue.geo_code == str(epci)
            ).order_by(Revenue.year).all()

            medians = {}
            poverty_rates = {}
            for record in results:
                medians[record.year] = record.median_revenue
                poverty_rates[record.year] = record.poverty_rate

            return {
                "epci": epci,
                "median_revenues": medians,
                "poverty_rates": poverty_rates
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des revenus pour l'EPCI {epci}: {str(e)}")
            return {
                "epci": epci,
                "median_revenues": {},
                "poverty_rates": {}
            }
        finally:
            self.close()

    def get_median_revenues_department(self, dep: str):
        """Récupère les revenus médians pour un département"""
        try:
            results = self.db.query(Revenue).filter(
                Revenue.geo_type == 'department',
                Revenue.geo_code == str(dep)
            ).order_by(Revenue.year).all()

            medians = {}
            poverty_rates = {}
            for record in results:
                medians[record.year] = record.median_revenue
                poverty_rates[record.year] = record.poverty_rate

            return {
                "department": dep,
                "median_revenues": medians,
                "poverty_rates": poverty_rates
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des revenus pour le département {dep}: {str(e)}")
            return {
                "department": dep,
                "median_revenues": {},
                "poverty_rates": {}
            }
        finally:
            self.close()

    def get_median_revenues_region(self, reg: str):
        """Récupère les revenus médians pour une région"""
        try:
            results = self.db.query(Revenue).filter(
                Revenue.geo_type == 'region',
                Revenue.geo_code == str(reg)
            ).order_by(Revenue.year).all()

            medians = {}
            poverty_rates = {}
            for record in results:
                medians[record.year] = record.median_revenue
                poverty_rates[record.year] = record.poverty_rate

            return {
                "region": reg,
                "median_revenues": medians,
                "poverty_rates": poverty_rates
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des revenus pour la région {reg}: {str(e)}")
            return {
                "region": reg,
                "median_revenues": {},
                "poverty_rates": {}
            }
        finally:
            self.close()

    def get_median_revenues_france(self):
        """Récupère les revenus médians pour la France entière"""
        try:
            results = self.db.query(Revenue).filter(
                Revenue.geo_type == 'france'
            ).order_by(Revenue.year).all()

            medians = {}
            poverty_rates = {}
            for record in results:
                medians[record.year] = record.median_revenue
                poverty_rates[record.year] = record.poverty_rate

            return {
                "median_revenues": medians,
                "poverty_rates": poverty_rates
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des revenus pour la France: {str(e)}")
            return {
                "median_revenues": {},
                "poverty_rates": {}
            }
        finally:
            self.close()

    def get_communes_revenues_by_epci(self, epci: str):
        """Récupère les revenus médians pour toutes les communes d'un EPCI"""
        try:
            # Récupérer les codes des communes de l'EPCI
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

            for commune_code, commune_name in communes:
                # Récupérer les données de revenus pour cette commune
                commune_data = self.db.query(Revenue).filter(
                    Revenue.geo_type == 'commune',
                    Revenue.geo_code == commune_code
                ).order_by(Revenue.year).all()

                median_revenues = {}
                poverty_rates = {}

                for record in commune_data:
                    median_revenues[record.year] = record.median_revenue
                    poverty_rates[record.year] = record.poverty_rate

                communes_data.append({
                    "code": commune_code,
                    "name": commune_name,
                    "median_revenues": median_revenues,
                    "poverty_rates": poverty_rates
                })

            # Trier par revenu médian de l'année la plus récente (si disponible)
            latest_year = max([max(c["median_revenues"].keys()) for c in communes_data if c["median_revenues"]], default=None)

            if latest_year:
                communes_data.sort(
                    key=lambda x: x["median_revenues"].get(latest_year, 0) or 0,
                    reverse=True
                )

            return {
                "epci": epci,
                "epci_name": epci_name,
                "communes_count": len(communes),
                "latest_year": latest_year,
                "communes": communes_data
            }

        except Exception as e:
            print(f"Erreur lors de la récupération des revenus pour l'EPCI {epci}: {str(e)}")
            return {
                "epci": epci,
                "epci_name": "",
                "communes_count": 0,
                "communes": []
            }
        finally:
            self.close()
