import pandas as pd
import numpy as np
from pathlib import Path

class PublicSafetyService:
    def __init__(self):
        # Chargement du fichier de géographie
        try:
            self.geo_df = pd.read_csv(
                Path("data/geography/COG_au_01-01-2024.csv"),
                delimiter=";",
                encoding="utf-8",
                dtype={"CODGEO": str, "DEP": str, "REG": str},
                usecols=["CODGEO", "DEP", "REG", "LIBGEO"]
            )
        except Exception as e:
            print(f"Erreur lors du chargement des données géographiques: {str(e)}")
            self.geo_df = pd.DataFrame()

        # Charger les données des communes (parquet)
        try:
            self.df_commune = pd.read_parquet(
                Path("data/public_safety/commune/donnee-comm-2023.parquet"),
                columns=["CODGEO_2023", "annee", "classe", "tauxpourmille"]
            )
            # Remplacer les NaN par 0
            self.df_commune['tauxpourmille'] = self.df_commune['tauxpourmille'].fillna(0)
        except Exception as e:
            print(f"Erreur lors du chargement des données communes: {str(e)}")
            self.df_commune = pd.DataFrame()

        # Charger les données des départements (CSV)
        try:
            self.df_department = pd.read_csv(
                Path("data/public_safety/department/donnee-dep-2023.csv"),
                sep=';',
                decimal=',',
                dtype={"Code.département": str},
                usecols=["Code.département", "annee", "classe", "tauxpourmille"]
            )
            # Remplacer les NaN par 0
            self.df_department['tauxpourmille'] = self.df_department['tauxpourmille'].fillna(0)
        except Exception as e:
            print(f"Erreur lors du chargement des données départements: {str(e)}")
            self.df_department = pd.DataFrame()

        # Charger les données des régions (CSV)
        try:
            self.df_region = pd.read_csv(
                Path("data/public_safety/region/donnee-reg-2023.csv"),
                sep=';',
                decimal=',',
                dtype={"Code.région": str},
                usecols=["Code.région", "annee", "classe", "tauxpourmille"]
            )
            # Remplacer les NaN par 0
            self.df_region['tauxpourmille'] = self.df_region['tauxpourmille'].fillna(0)
        except Exception as e:
            print(f"Erreur lors du chargement des données régions: {str(e)}")
            self.df_region = pd.DataFrame()

    def clean_data_for_json(self, df):
        """Nettoie les données pour la sérialisation JSON"""
        df_clean = df.copy()
        # Convertir tous les nombres en float Python standard
        df_clean['annee'] = df_clean['annee'].astype(int)
        df_clean['tauxpourmille'] = df_clean['tauxpourmille'].astype(float)
        # Remplacer les NaN par 0
        df_clean = df_clean.fillna(0)
        return df_clean

    def get_by_commune(self, code: str):
        """Récupère les données de sécurité pour une commune et ses zones géographiques parentes"""
        try:
            # Récupérer les codes département et région de la commune
            geo_info = self.geo_df[self.geo_df['CODGEO'] == str(code)]

            if geo_info.empty:
                return {
                    "commune": {"code": code, "name": None, "data": []},
                    "department": {"code": "", "name": None, "data": []},
                    "region": {"code": "", "name": None, "data": []}
                }

            geo_info = geo_info.iloc[0]
            dep_code = geo_info['DEP']
            reg_code = geo_info['REG']

            # Données de la commune
            commune_data = self.df_commune[
                self.df_commune['CODGEO_2023'] == str(code)
            ][['annee', 'classe', 'tauxpourmille']]
            commune_data = self.clean_data_for_json(commune_data)

            # Données du département
            dep_data = self.df_department[
                self.df_department['Code.département'] == str(dep_code)
            ][['annee', 'classe', 'tauxpourmille']]
            dep_data = self.clean_data_for_json(dep_data)

            # Données de la région
            reg_data = self.df_region[
                self.df_region['Code.région'] == str(reg_code)
            ][['annee', 'classe', 'tauxpourmille']]
            reg_data = self.clean_data_for_json(reg_data)

            return {
                "commune": {
                    "code": code,
                    "name": geo_info['LIBGEO'],
                    "data": commune_data.to_dict(orient="records")
                },
                "department": {
                    "code": dep_code,
                    "name": f"Département {dep_code}",
                    "data": dep_data.to_dict(orient="records")
                },
                "region": {
                    "code": reg_code,
                    "name": f"Région {reg_code}",
                    "data": reg_data.to_dict(orient="records")
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_commune: {str(e)}")
            return {
                "commune": {"code": code, "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {"code": "", "name": None, "data": []}
            }

    def get_by_department(self, dep: str):
        """Récupère les données de sécurité pour un département et sa région parente"""
        try:
            # Récupérer le code région du département
            geo_info = self.geo_df[self.geo_df['DEP'] == str(dep)]

            if geo_info.empty:
                return {
                    "commune": {"code": "", "name": None, "data": []},
                    "department": {"code": dep, "name": None, "data": []},
                    "region": {"code": "", "name": None, "data": []}
                }

            geo_info = geo_info.iloc[0]
            reg_code = geo_info['REG']

            # Données du département
            dep_data = self.df_department[
                self.df_department['Code.département'] == str(dep)
            ][['annee', 'classe', 'tauxpourmille']]
            dep_data = self.clean_data_for_json(dep_data)

            # Données de la région
            reg_data = self.df_region[
                self.df_region['Code.région'] == str(reg_code)
            ][['annee', 'classe', 'tauxpourmille']]
            reg_data = self.clean_data_for_json(reg_data)

            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {
                    "code": dep,
                    "name": f"Département {dep}",
                    "data": dep_data.to_dict(orient="records")
                },
                "region": {
                    "code": reg_code,
                    "name": f"Région {reg_code}",
                    "data": reg_data.to_dict(orient="records")
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_department: {str(e)}")
            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": dep, "name": None, "data": []},
                "region": {"code": "", "name": None, "data": []}
            }

    def get_by_region(self, reg: str):
        """Récupère les données de sécurité pour une région"""
        try:
            # Données de la région
            reg_data = self.df_region[
                self.df_region['Code.région'] == str(reg)
            ][['annee', 'classe', 'tauxpourmille']]
            reg_data = self.clean_data_for_json(reg_data)

            if reg_data.empty:
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
                    "data": reg_data.to_dict(orient="records")
                }
            }

        except Exception as e:
            print(f"Erreur dans get_by_region: {str(e)}")
            return {
                "commune": {"code": "", "name": None, "data": []},
                "department": {"code": "", "name": None, "data": []},
                "region": {"code": reg, "name": None, "data": []}
            }
