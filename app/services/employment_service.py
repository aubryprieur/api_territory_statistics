import pandas as pd
from pathlib import Path

class EmploymentService:
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

        # Charger les données d'emploi et de population active
        try:
            self.df_active = pd.read_csv(
                Path("data/employment/activity/base-cc-emploi-pop-active-2021.CSV"),
                delimiter=";",
                encoding="utf-8",
                dtype={"CODGEO": str}
            )
        except Exception as e:
            print(f"Erreur lors du chargement des données de population active: {str(e)}")
            self.df_active = pd.DataFrame()

        # Charger les données des caractéristiques d'emploi
        try:
            self.df_caract = pd.read_csv(
                Path("data/employment/characteristics/base-cc-caract_emp-2021.CSV"),
                delimiter=";",
                encoding="utf-8",
                dtype={"CODGEO": str}
            )
        except Exception as e:
            print(f"Erreur lors du chargement des caractéristiques d'emploi: {str(e)}")
            self.df_caract = pd.DataFrame()

    def calculate_rates(self, active_data):
        """Calcule les taux d'activité et d'emploi des femmes"""
        try:
            if active_data.empty:
                return {
                    "activity_rate": 0,
                    "employment_rate": 0
                }

            # Taux d'activité des femmes (actifs / population totale)
            # P21_FACT1564 : Femmes actives de 15-64 ans en 2021
            # P21_F1564 : Femmes de 15-64 ans en 2021
            women_active = active_data['P21_FACT1564'].sum()
            women_total = active_data['P21_F1564'].sum()
            activity_rate = (women_active / women_total * 100) if women_total > 0 else 0

            # Taux d'emploi des femmes (actifs occupés / population totale)
            # P21_FACTOCC1564 : Femmes actives occupées de 15-64 ans en 2021
            women_employed = active_data['P21_FACTOCC1564'].sum()
            employment_rate = (women_employed / women_total * 100) if women_total > 0 else 0

            return {
                "activity_rate": round(float(activity_rate), 1),
                "employment_rate": round(float(employment_rate), 1)
            }
        except Exception as e:
            print(f"Erreur dans calculate_rates: {str(e)}")
            raise

    def get_commune_rates(self, code: str):
        """Récupère les taux pour une commune"""
        try:
            commune_active = self.df_active[self.df_active['CODGEO'] == str(code)]
            geo_info = self.geo_df[self.geo_df['CODGEO'] == str(code)]

            if geo_info.empty:
                return {"error": "Commune non trouvée"}

            rates = self.calculate_rates(commune_active)
            return {
                "territory_type": "commune",
                "code": code,
                "name": geo_info.iloc[0]['LIBGEO'],
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_commune_rates: {str(e)}")
            return {
                "error": str(e),
                "territory_type": "commune",
                "code": code,
                "rates": {"activity_rate": 0, "employment_rate": 0}
            }

    def get_epci_rates(self, epci: str):
        """Récupère les taux pour un EPCI"""
        try:
            communes = self.geo_df[self.geo_df['EPCI'] == str(epci)]['CODGEO'].tolist()
            epci_active = self.df_active[self.df_active['CODGEO'].isin(communes)]

            rates = self.calculate_rates(epci_active)
            return {
                "territory_type": "epci",
                "code": epci,
                "name": f"EPCI {epci}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_epci_rates: {str(e)}")
            return {
                "error": str(e),
                "territory_type": "epci",
                "code": epci,
                "rates": {"activity_rate": 0, "employment_rate": 0}
            }

    def get_department_rates(self, dep: str):
        """Récupère les taux pour un département"""
        try:
            communes = self.geo_df[self.geo_df['DEP'] == str(dep)]['CODGEO'].tolist()
            dep_active = self.df_active[self.df_active['CODGEO'].isin(communes)]

            rates = self.calculate_rates(dep_active)
            return {
                "territory_type": "department",
                "code": dep,
                "name": f"Département {dep}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_department_rates: {str(e)}")
            return {
                "error": str(e),
                "territory_type": "department",
                "code": dep,
                "rates": {"activity_rate": 0, "employment_rate": 0}
            }

    def get_region_rates(self, reg: str):
        """Récupère les taux pour une région"""
        try:
            communes = self.geo_df[self.geo_df['REG'] == str(reg)]['CODGEO'].tolist()
            reg_active = self.df_active[self.df_active['CODGEO'].isin(communes)]

            rates = self.calculate_rates(reg_active)
            return {
                "territory_type": "region",
                "code": reg,
                "name": f"Région {reg}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_region_rates: {str(e)}")
            return {
                "error": str(e),
                "territory_type": "region",
                "code": reg,
                "rates": {"activity_rate": 0, "employment_rate": 0}
            }

    def get_france_rates(self):
        """Récupère les taux pour la France entière"""
        try:
            rates = self.calculate_rates(self.df_active)
            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_france_rates: {str(e)}")
            return {
                "error": str(e),
                "territory_type": "country",
                "code": "FR",
                "rates": {"activity_rate": 0, "employment_rate": 0}
            }
