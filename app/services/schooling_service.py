import pandas as pd
from pathlib import Path

class SchoolingService:
    def __init__(self):
        # Chargement du fichier de géographie
        try:
            self.geo_df = pd.read_csv(
                Path("data/geography/COG_au_01-01-2024.csv"),
                delimiter=";",
                encoding="utf-8",
                dtype={"CODGEO": str, "DEP": str, "REG": str, "EPCI": str},
                usecols=["CODGEO", "DEP", "REG", "EPCI", "LIBGEO"]
            )
        except Exception as e:
            print(f"Erreur lors du chargement des données géographiques: {str(e)}")
            self.geo_df = pd.DataFrame()

        # Charger les données de scolarisation pour chaque année
        self.dfs = {}
        for year in range(2017, 2022):
            try:
                self.dfs[year] = pd.read_csv(
                    Path(f"data/education/schooling/TD_FOR1_{year}.csv"),
                    delimiter=";",
                    encoding="utf-8",
                    dtype={"CODGEO": str}
                )
            except Exception as e:
                print(f"Erreur lors du chargement des données {year}: {str(e)}")
                self.dfs[year] = pd.DataFrame()

    def _calculate_schooling_rates(self, data, year):
        """Calcule les taux de scolarisation des enfants de 2 ans et 3-5 ans"""
        try:
            # Pour les enfants de 2 ans
            children_2y = data[
                (data["AGEFORD"] == 2) &
                (data["SEXE"].isin([1, 2]))
            ]
            total_children_2y = children_2y["NB"].sum()
            schooled_2y = children_2y[
                children_2y["ILETUR"].isin(["1", "2", "3", "4", "5"])
            ]
            schooled_children_2y = schooled_2y["NB"].sum()
            schooling_rate_2y = (schooled_children_2y / total_children_2y * 100) if total_children_2y > 0 else 0

            # Pour les enfants de 3 à 5 ans
            children_3_5y = data[
                (data["AGEFORD"].isin([3, 4, 5])) &
                (data["SEXE"].isin([1, 2]))
            ]
            total_children_3_5y = children_3_5y["NB"].sum()
            schooled_3_5y = children_3_5y[
                children_3_5y["ILETUR"].isin(["1", "2", "3", "4", "5"])
            ]
            schooled_children_3_5y = schooled_3_5y["NB"].sum()
            schooling_rate_3_5y = (schooled_children_3_5y / total_children_3_5y * 100) if total_children_3_5y > 0 else 0

            return {
                # Statistiques pour les 2 ans
                "total_children_2y": float(total_children_2y),
                "schooled_children_2y": float(schooled_children_2y),
                "schooling_rate_2y": round(float(schooling_rate_2y), 1),
                # Statistiques pour les 3-5 ans
                "total_children_3_5y": float(total_children_3_5y),
                "schooled_children_3_5y": float(schooled_children_3_5y),
                "schooling_rate_3_5y": round(float(schooling_rate_3_5y), 1)
            }
        except Exception as e:
            print(f"Erreur dans le calcul des taux pour l'année {year}: {str(e)}")
            return {
                "total_children_2y": 0,
                "schooled_children_2y": 0,
                "schooling_rate_2y": 0,
                "total_children_3_5y": 0,
                "schooled_children_3_5y": 0,
                "schooling_rate_3_5y": 0
            }

    def get_commune_schooling(self, code: str):
        """Récupère les données de scolarisation pour une commune"""
        try:
            # Vérifier si la commune existe
            geo_info = self.geo_df[self.geo_df['CODGEO'] == str(code)]
            if geo_info.empty:
                return {
                    "territory_type": "commune",
                    "code": code,
                    "name": "Commune inconnue",
                    "data": {}
                }

            # Calculer les taux pour chaque année
            results = {}
            for year in range(2017, 2022):
                df_year = self.dfs[year]
                commune_data = df_year[df_year["CODGEO"] == str(code)]
                results[year] = self._calculate_schooling_rates(commune_data, year)

            return {
                "territory_type": "commune",
                "code": code,
                "name": geo_info.iloc[0]['LIBGEO'],
                "data": results
            }
        except Exception as e:
            print(f"Erreur pour la commune {code}: {str(e)}")
            return {
                "territory_type": "commune",
                "code": code,
                "name": "Erreur",
                "data": {}
            }

    def get_epci_schooling(self, epci: str):
        """Récupère les données de scolarisation pour un EPCI"""
        try:
            # Récupérer toutes les communes de l'EPCI
            communes = self.geo_df[self.geo_df['EPCI'] == str(epci)]['CODGEO'].tolist()
            if not communes:
                return {
                    "territory_type": "epci",
                    "code": epci,
                    "name": "EPCI inconnu",
                    "data": {}
                }

            # Calculer les taux pour chaque année
            results = {}
            for year in range(2017, 2022):
                df_year = self.dfs[year]
                epci_data = df_year[df_year["CODGEO"].isin(communes)]
                results[year] = self._calculate_schooling_rates(epci_data, year)

            return {
                "territory_type": "epci",
                "code": epci,
                "name": f"EPCI {epci}",
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

    def get_department_schooling(self, dep: str):
        """Récupère les données de scolarisation pour un département"""
        try:
            communes = self.geo_df[self.geo_df['DEP'] == str(dep)]['CODGEO'].tolist()
            if not communes:
                return {
                    "territory_type": "department",
                    "code": dep,
                    "name": "Département inconnu",
                    "data": {}
                }

            results = {}
            for year in range(2017, 2022):
                df_year = self.dfs[year]
                dep_data = df_year[df_year["CODGEO"].isin(communes)]
                results[year] = self._calculate_schooling_rates(dep_data, year)

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

    def get_region_schooling(self, reg: str):
        """Récupère les données de scolarisation pour une région"""
        try:
            communes = self.geo_df[self.geo_df['REG'] == str(reg)]['CODGEO'].tolist()
            if not communes:
                return {
                    "territory_type": "region",
                    "code": reg,
                    "name": "Région inconnue",
                    "data": {}
                }

            results = {}
            for year in range(2017, 2022):
                df_year = self.dfs[year]
                reg_data = df_year[df_year["CODGEO"].isin(communes)]
                results[year] = self._calculate_schooling_rates(reg_data, year)

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

    def get_france_schooling(self):
        """Récupère les données de scolarisation pour la France entière"""
        try:
            results = {}
            for year in range(2017, 2022):
                df_year = self.dfs[year]
                results[year] = self._calculate_schooling_rates(df_year, year)

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
                "name": "Erreur",
                "data": {}
            }
