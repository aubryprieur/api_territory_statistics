from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import SessionLocal
from app.models import Historical, GeoCode

class HistoricalService:
    def __init__(self):
        self.db = SessionLocal()

    def close(self):
        """Ferme la connexion à la base de données"""
        self.db.close()

    def _format_historical_data(self, data: List[Historical]) -> List[dict]:
        """Convertit les données du modèle au format attendu par l'API"""
        result = []
        for item in data:
            result.append({
                "CODGEO": item.codgeo,
                "D68_POP": item.pop_1968 or 0.0,
                "D75_POP": item.pop_1975 or 0.0,
                "D82_POP": item.pop_1982 or 0.0,
                "D90_POP": item.pop_1990 or 0.0,
                "D99_POP": item.pop_1999 or 0.0,
                "P10_POP": item.pop_2010 or 0.0,
                "P15_POP": item.pop_2015 or 0.0,
                "P21_POP": item.pop_2021 or 0.0
            })
        return result

    def get_all_data(self) -> List[dict]:
        """Récupère toutes les données historiques"""
        try:
            data = self.db.query(Historical).all()
            return self._format_historical_data(data)
        except Exception as e:
            print(f"Erreur dans get_all_data: {str(e)}")
            return []
        finally:
            self.close()

    def get_by_code(self, codgeo: str) -> List[dict]:
        """Récupère les données historiques pour une commune spécifique"""
        try:
            data = self.db.query(Historical).filter(Historical.codgeo == str(codgeo)).all()
            return self._format_historical_data(data)
        except Exception as e:
            print(f"Erreur dans get_by_code: {str(e)}")
            return []
        finally:
            self.close()

    def get_communes_historical_by_epci(self, epci: str):
        """Récupère l'évolution historique de population pour toutes les communes d'un EPCI"""
        try:
            # Établir une connexion à la base de données
            db = SessionLocal()

            # Récupérer les communes de l'EPCI
            communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()

            if not communes:
                return {
                    "epci": epci,
                    "epci_name": "",
                    "communes_count": 0,
                    "communes": []
                }

            # Récupérer le nom de l'EPCI
            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # Initialiser les totaux de l'EPCI par année
            epci_totals = {
                "1968": 0.0,
                "1975": 0.0,
                "1982": 0.0,
                "1990": 0.0,
                "1999": 0.0,
                "2010": 0.0,
                "2015": 0.0,
                "2021": 0.0
            }

            # Récupérer les données pour chaque commune
            communes_data = []
            fastest_growth = -100  # Initialiser à une valeur négative
            fastest_commune = None
            most_populated_commune = None
            highest_population = 0

            for code, name in communes:
                # Récupérer les données historiques pour cette commune
                historical_data = db.query(Historical).filter(Historical.codgeo == code).first()

                if historical_data:
                    # Extraire l'historique de population
                    population_history = {
                        "1968": self._safe_float(historical_data.pop_1968),
                        "1975": self._safe_float(historical_data.pop_1975),
                        "1982": self._safe_float(historical_data.pop_1982),
                        "1990": self._safe_float(historical_data.pop_1990),
                        "1999": self._safe_float(historical_data.pop_1999),
                        "2010": self._safe_float(historical_data.pop_2010),
                        "2015": self._safe_float(historical_data.pop_2015),
                        "2021": self._safe_float(historical_data.pop_2021)
                    }

                    # Ajouter aux totaux de l'EPCI
                    for year in epci_totals.keys():
                        epci_totals[year] += population_history[year]

                    # Calculer les évolutions entre périodes
                    evolution_percentage = {}

                    # Évolution sur la période complète (1968-2021)
                    if population_history["1968"] > 0 and population_history["2021"] > 0:
                        long_term = ((population_history["2021"] - population_history["1968"]) /
                                    population_history["1968"] * 100)
                        evolution_percentage["1968-2021"] = round(long_term, 2)

                        # Identifier la commune avec la plus forte croissance
                        if long_term > fastest_growth:
                            fastest_growth = long_term
                            fastest_commune = name

                    # Évolution récente (2015-2021)
                    if population_history["2015"] > 0 and population_history["2021"] > 0:
                        recent = ((population_history["2021"] - population_history["2015"]) /
                                 population_history["2015"] * 100)
                        evolution_percentage["2015-2021"] = round(recent, 2)

                    # Identifier la commune la plus peuplée
                    if population_history["2021"] > highest_population:
                        highest_population = population_history["2021"]
                        most_populated_commune = name

                    communes_data.append({
                        "code": code,
                        "name": name,
                        "population_history": population_history,
                        "evolution_percentage": evolution_percentage,
                        "latest_population": population_history["2021"]
                    })
                else:
                    # Commune sans données historiques
                    communes_data.append({
                        "code": code,
                        "name": name,
                        "population_history": {},
                        "evolution_percentage": {},
                        "latest_population": 0
                    })

            # Calculer les évolutions pour l'EPCI
            epci_evolution = {}

            # Évolution sur la période complète (1968-2021)
            if epci_totals["1968"] > 0 and epci_totals["2021"] > 0:
                epci_long_term = ((epci_totals["2021"] - epci_totals["1968"]) /
                                epci_totals["1968"] * 100)
                epci_evolution["1968-2021"] = round(epci_long_term, 2)

            # Évolution récente (2015-2021)
            if epci_totals["2015"] > 0 and epci_totals["2021"] > 0:
                epci_recent = ((epci_totals["2021"] - epci_totals["2015"]) /
                             epci_totals["2015"] * 100)
                epci_evolution["2015-2021"] = round(epci_recent, 2)

            # Trier les communes par population décroissante (dernière année)
            communes_data.sort(key=lambda x: x["latest_population"], reverse=True)

            # Supprimer le champ temporaire utilisé pour le tri
            for commune in communes_data:
                commune.pop("latest_population", None)

            return {
                "epci": epci,
                "epci_name": epci_name,
                "communes_count": len(communes),
                "most_populated_commune": most_populated_commune,
                "fastest_growing_commune": fastest_commune,
                "epci_population_history": epci_totals,
                "epci_evolution_percentage": epci_evolution,
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des données historiques pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "epci": epci,
                "epci_name": "",
                "communes_count": 0,
                "communes": []
            }
        finally:
            db.close()

    def _safe_float(self, value):
        """Convertit une valeur en float de manière sécurisée"""
        try:
            if value is None:
                return 0.0
            float_val = float(value)
            return float_val
        except (ValueError, TypeError):
            return 0.0
