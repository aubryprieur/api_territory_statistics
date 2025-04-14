from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Birth, GeoCode

class BirthService:
    def __init__(self):
        self.db = SessionLocal()

    def get_by_code(self, geo: str):
        """
        Récupère les données de naissance pour une commune spécifique depuis PostgreSQL.
        """
        return self.db.query(Birth).filter(Birth.geo == geo).order_by(Birth.time_period).all()

    def get_by_type(self, geo_object: str):
        """
        Récupère les données de naissance pour un type de territoire donné (ex: COM, DEP, REG).
        """
        return self.db.query(Birth).filter(Birth.geo_object == geo_object).all()

    def get_births_trend(self, geo: str):
        """
        Agrège les naissances par année pour une commune.
        """
        results = (
            self.db.query(Birth.time_period, Birth.obs_value)
            .filter(Birth.geo == geo)
            .order_by(Birth.time_period)
            .all()
        )
        return {year: births for year, births in results}

    def get_births_by_epci_communes(self, epci: str):
        """Récupère les données de naissances pour toutes les communes d'un EPCI"""
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
                    "total_births": 0.0,
                    "years_available": [],
                    "communes": []
                }

            # Récupérer le nom de l'EPCI
            epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
            epci_name = epci_info[0] if epci_info else f"EPCI {epci}"

            # Récupérer les données pour chaque commune
            communes_data = []
            epci_births_by_year = {}
            all_years = set()
            highest_births = 0
            highest_births_commune = None

            for code, name in communes:
                code_str = str(code).strip()

                print(f"Récupération des naissances pour {name} (code: {code_str})")

                # Filtrer sur geo ET geo_object pour obtenir uniquement les données communales
                births_data = db.query(
                    Birth.time_period,
                    func.sum(Birth.obs_value).label('total_births')
                ).filter(
                    Birth.geo == code_str,
                    Birth.geo_object == "COM"  # Filtrer uniquement les données communales
                ).group_by(
                    Birth.time_period
                ).order_by(
                    Birth.time_period
                ).all()

                print(f"  -> {len(births_data)} années trouvées")

                births_by_year = {}
                total_births = 0

                for year, count in births_data:
                    count_float = float(count)
                    births_by_year[year] = count_float
                    total_births += count_float
                    all_years.add(year)

                    print(f"  -> Année {year}: {count_float} naissances")

                    # Mettre à jour les totaux de l'EPCI
                    if year not in epci_births_by_year:
                        epci_births_by_year[year] = 0
                    epci_births_by_year[year] += count_float

                latest_year = max(births_by_year.keys()) if births_by_year else None

                communes_data.append({
                    "code": code_str,
                    "name": name,
                    "births_by_year": births_by_year,
                    "total_births": total_births,
                    "latest_year": latest_year
                })

                # Identifier la commune avec le plus de naissances
                if total_births > highest_births:
                    highest_births = total_births
                    highest_births_commune = name

            # Trier les communes par nombre total de naissances décroissant
            communes_data.sort(key=lambda x: x["total_births"], reverse=True)

            # Calculer le total des naissances pour l'EPCI
            total_epci_births = sum(epci_births_by_year.values())

            # Trier les années disponibles
            years_available = sorted(list(all_years))

            return {
                "epci": epci,
                "epci_name": epci_name,
                "communes_count": len(communes),
                "total_births": total_epci_births,
                "years_available": years_available,
                "highest_births_commune": highest_births_commune,
                "epci_births_by_year": epci_births_by_year,  # Ajout des naissances par année pour l'EPCI
                "communes": communes_data
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des naissances pour l'EPCI {epci}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "epci": epci,
                "epci_name": "",
                "communes_count": 0,
                "total_births": 0.0,
                "years_available": [],
                "communes": []
            }
        finally:
            db.close()
