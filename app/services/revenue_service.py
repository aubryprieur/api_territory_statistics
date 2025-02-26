from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional, List
from app.database import SessionLocal
from app.models import Revenue

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
