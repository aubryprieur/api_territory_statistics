# app/services/childcare_service.py
import pandas as pd
from pathlib import Path

class ChildcareService:
    def __init__(self):
       self.dfs = {}
       # Charger les données pour chaque niveau géographique
       try:
           self.dfs['commune'] = pd.read_parquet(Path("data/childcare/commune/txcouv_pe_com_2017_2022.parquet"))
           self.dfs['epci'] = pd.read_parquet(Path("data/childcare/epci/txcouv_pe_epci_2017_2022.parquet"))
           self.dfs['department'] = pd.read_parquet(Path("data/childcare/department/txcouv_pe_dep_2017_2022.parquet"))
           self.dfs['region'] = pd.read_parquet(Path("data/childcare/region/txcouv_pe_reg_2017_2022.parquet"))
           self.dfs['france'] = pd.read_parquet(Path("data/childcare/france/txcouv_pe_nat_2017_2022.parquet"))
       except Exception as e:
           print(f"Erreur lors du chargement des fichiers parquet: {str(e)}")

    def get_coverage_by_commune(self, commune: str, start_year: int = None, end_year: int = None):
        try:
            df = self.dfs['commune']
            data = df[df['numcom'] == str(commune)].copy()

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}
            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "commune_name": row['nomcom'],
                    "epci": {
                        "code": row['numepci'],
                        "name": row['nomepci']
                    },
                    "department": {
                        "code": row['numdep'],
                        "name": row['nomdep']
                    },
                    "coverage_rates": {
                        "eaje_psu": float(row['txcouv_psu_col_com']),
                        "eaje_hors_psu": float(row['txcouv_hors_psu_col_com']),
                        "eaje_total": float(row['txcouv_eaje_com']),
                        "preschool": float(row['txcouv_prescol_com']),
                        "childminder": float(row['txcouv_am_ind_com']),
                        "home_care": float(row['txcouv_gad_ind_com']),
                        "individual_total": float(row['txcouv_ind_com']),
                        "global": float(row['txcouv_com'])
                    }
                }

            return {
                "commune": commune,
                "coverage_data": result
            }
        except Exception as e:
            return {"error": str(e)}

    def get_coverage_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        try:
            df = self.dfs['epci']
            data = df[df['numepci'] == str(epci)].copy()

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}
            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "epci_name": row['nomepci'],
                    "department": {
                        "code": row['numdep'],
                        "name": row['nomdep']
                    },
                    "coverage_rates": {
                        "eaje_psu": float(row['txcouv_psu_col_epci']),
                        "eaje_hors_psu": float(row['txcouv_hors_psu_col_epci']),
                        "eaje_total": float(row['txcouv_eaje_epci']),
                        "preschool": float(row['txcouv_prescol_epci']),
                        "childminder": float(row['txcouv_am_ind_epci']),
                        "home_care": float(row['txcouv_gad_ind_epci']),
                        "individual_total": float(row['txcouv_ind_epci']),
                        "global": float(row['txcouv_epci'])
                    }
                }

            return {
                "epci": epci,
                "coverage_data": result
            }
        except Exception as e:
            return {"error": str(e)}

    def get_coverage_by_department(self, department: str, start_year: int = None, end_year: int = None):
        try:
            df = self.dfs['department']
            data = df[df['numdep'] == str(department)].copy()

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}
            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "department_name": row['nomdep'],
                    "region": {
                        "code": row['numregi'],
                        "name": row['nomregi']
                    },
                    "coverage_rates": {
                        "eaje_psu": float(row['txcouv_psu_col_dep']),
                        "eaje_hors_psu": float(row['txcouv_hors_psu_col_dep']),
                        "eaje_total": float(row['txcouv_eaje_dep']),
                        "preschool": float(row['txcouv_prescol_dep']),
                        "childminder": float(row['txcouv_am_ind_dep']),
                        "home_care": float(row['txcouv_gad_ind_dep']),
                        "individual_total": float(row['txcouv_ind_dep']),
                        "global": float(row['txcouv_dep'])
                    }
                }

            return {
                "department": department,
                "coverage_data": result
            }
        except Exception as e:
            return {"error": str(e)}

    def get_coverage_by_region(self, region: str, start_year: int = None, end_year: int = None):
        try:
            df = self.dfs['region']
            data = df[df['numregi'] == str(region)].copy()

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}
            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "region_name": row['nomregi'],
                    "coverage_rates": {
                        "eaje_psu": float(row['txcouv_psu_col_reg']),
                        "eaje_hors_psu": float(row['txcouv_hors_psu_col_reg']),
                        "eaje_total": float(row['txcouv_eaje_reg']),
                        "preschool": float(row['txcouv_prescol_reg']),
                        "childminder": float(row['txcouv_am_ind_reg']),
                        "home_care": float(row['txcouv_gad_ind_reg']),
                        "individual_total": float(row['txcouv_ind_reg']),
                        "global": float(row['txcouv_reg'])
                    }
                }

            return {
                "region": region,
                "coverage_data": result
            }
        except Exception as e:
            return {"error": str(e)}

    def get_coverage_france(self, start_year: int = None, end_year: int = None):
       try:
           df = self.dfs['france']
           data = df.copy()

           if start_year and end_year:
               data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

           result = {}
           for _, row in data.iterrows():
               year = int(row['annee'])
               result[year] = {
                   "name": row['national'],
                   "coverage_rates": {
                       "eaje_psu": float(row['txcouv_psu_nat']),
                       "eaje_hors_psu": float(row['txcouv_hors_psu_col_nat']),
                       "eaje_total": float(row['txcouv_eaje_nat']),
                       "preschool": float(row['txcouv_prescol_nat']),
                       "childminder": float(row['txcouv_am_nat']),
                       "home_care": float(row['txcouv_gad_nat']),
                       "individual_total": float(row['txcouv_ind_nat']),
                       "global": float(row['txcouv_nat'])
                   }
               }

           return {
               "coverage_data": result
           }
       except Exception as e:
           return {"error": str(e)}
