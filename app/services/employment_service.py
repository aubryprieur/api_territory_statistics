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

    def calculate_rates(self, active_data, caract_data):
        """Calcule tous les taux"""
        try:
            if active_data.empty or caract_data.empty:
                return {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }

            # Taux d'activité des femmes (actifs / population totale)
            women_active = active_data['P21_FACT1564'].sum()
            women_total = active_data['P21_F1564'].sum()
            activity_rate = (women_active / women_total * 100) if women_total > 0 else 0

            # Taux d'emploi des femmes (actifs occupés / population totale)
            women_employed = active_data['P21_FACTOCC1564'].sum()
            employment_rate = (women_employed / women_total * 100) if women_total > 0 else 0

            # Taux de temps partiel des femmes salariées
            # Pour les 25-54 ans
            women_part_time_25_54 = caract_data['P21_FSAL2554_TP'].sum()
            women_total_25_54 = caract_data['P21_FSAL2554'].sum()
            part_time_rate_25_54 = (women_part_time_25_54 / women_total_25_54 * 100) if women_total_25_54 > 0 else 0

            # Pour les 15-64 ans
            women_part_time_15_64 = caract_data['P21_FSAL1564_TP'].sum()
            women_total_15_64 = caract_data['P21_FSAL1564'].sum()
            part_time_rate_15_64 = (women_part_time_15_64 / women_total_15_64 * 100) if women_total_15_64 > 0 else 0

            return {
                "activity_rate": round(float(activity_rate), 1),
                "employment_rate": round(float(employment_rate), 1),
                "part_time_rate_25_54": round(float(part_time_rate_25_54), 1),
                "part_time_rate_15_64": round(float(part_time_rate_15_64), 1)
            }
        except Exception as e:
            print(f"Erreur dans calculate_rates: {str(e)}")
            raise

    def get_commune_rates(self, code: str):
        """Récupère les taux pour une commune"""
        try:
            commune_active = self.df_active[self.df_active['CODGEO'] == str(code)]
            commune_caract = self.df_caract[self.df_caract['CODGEO'] == str(code)]
            geo_info = self.geo_df[self.geo_df['CODGEO'] == str(code)]

            if geo_info.empty:
                return {
                    "territory_type": "commune",
                    "code": code,
                    "name": "Commune inconnue",
                    "rates": {
                        "activity_rate": 0,
                        "employment_rate": 0,
                        "part_time_rate_25_54": 0,
                        "part_time_rate_15_64": 0
                    }
                }

            rates = self.calculate_rates(commune_active, commune_caract)
            return {
                "territory_type": "commune",
                "code": code,
                "name": geo_info.iloc[0]['LIBGEO'],
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_commune_rates: {str(e)}")
            return {
                "territory_type": "commune",
                "code": code,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }

    def get_epci_rates(self, epci: str):
        """Récupère les taux pour un EPCI"""
        try:
            communes = self.geo_df[self.geo_df['EPCI'] == str(epci)]['CODGEO'].tolist()
            epci_active = self.df_active[self.df_active['CODGEO'].isin(communes)]
            epci_caract = self.df_caract[self.df_caract['CODGEO'].isin(communes)]

            rates = self.calculate_rates(epci_active, epci_caract)
            return {
                "territory_type": "epci",
                "code": epci,
                "name": f"EPCI {epci}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_epci_rates: {str(e)}")
            return {
                "territory_type": "epci",
                "code": epci,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }

    def get_department_rates(self, dep: str):
        """Récupère les taux pour un département"""
        try:
            communes = self.geo_df[self.geo_df['DEP'] == str(dep)]['CODGEO'].tolist()
            dep_active = self.df_active[self.df_active['CODGEO'].isin(communes)]
            dep_caract = self.df_caract[self.df_caract['CODGEO'].isin(communes)]

            rates = self.calculate_rates(dep_active, dep_caract)
            return {
                "territory_type": "department",
                "code": dep,
                "name": f"Département {dep}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_department_rates: {str(e)}")
            return {
                "territory_type": "department",
                "code": dep,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }

    def get_region_rates(self, reg: str):
        """Récupère les taux pour une région"""
        try:
            communes = self.geo_df[self.geo_df['REG'] == str(reg)]['CODGEO'].tolist()
            reg_active = self.df_active[self.df_active['CODGEO'].isin(communes)]
            reg_caract = self.df_caract[self.df_caract['CODGEO'].isin(communes)]

            rates = self.calculate_rates(reg_active, reg_caract)
            return {
                "territory_type": "region",
                "code": reg,
                "name": f"Région {reg}",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_region_rates: {str(e)}")
            return {
                "territory_type": "region",
                "code": reg,
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }

    def get_france_rates(self):
        """Récupère les taux pour la France entière"""
        try:
            rates = self.calculate_rates(self.df_active, self.df_caract)
            return {
                "territory_type": "country",
                "code": "FR",
                "name": "France",
                "rates": rates
            }
        except Exception as e:
            print(f"Erreur dans get_france_rates: {str(e)}")
            return {
                "territory_type": "country",
                "code": "FR",
                "name": "Erreur",
                "rates": {
                    "activity_rate": 0,
                    "employment_rate": 0,
                    "part_time_rate_25_54": 0,
                    "part_time_rate_15_64": 0
                }
            }
