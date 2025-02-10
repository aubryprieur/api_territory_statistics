import pandas as pd
from pathlib import Path

class ChildcareService:
    def __init__(self):
        self.dfs = {}
        self.alternative_dfs = {}  # Renommé de historical_dfs à alternative_dfs

        # Charger les données parquet actuelles
        try:
            self.dfs['commune'] = pd.read_parquet(Path("data/childcare/commune/current/txcouv_pe_com_2017_2022.parquet"))
            self.dfs['epci'] = pd.read_parquet(Path("data/childcare/epci/txcouv_pe_epci_2017_2022.parquet"))
            self.dfs['department'] = pd.read_parquet(Path("data/childcare/department/txcouv_pe_dep_2017_2022.parquet"))
            self.dfs['region'] = pd.read_parquet(Path("data/childcare/region/txcouv_pe_reg_2017_2022.parquet"))
            self.dfs['france'] = pd.read_parquet(Path("data/childcare/france/txcouv_pe_nat_2017_2022.parquet"))

            # Charger les données alternatives CSV
            for year in [2020, 2021]:
                csv_path = Path(f"data/childcare/commune/alternative/TAUXCOUV{year}.csv")
                if csv_path.exists():
                    self.alternative_dfs[year] = pd.read_csv(
                        csv_path,
                        delimiter=";",
                        encoding="utf-8",
                        low_memory=False
                    )
        except Exception as e:
            print(f"Erreur lors du chargement des fichiers: {str(e)}")

    def get_coverage_from_alternative(self, commune: str, year: int):
        """Récupère les données de couverture depuis les fichiers CSV alternatifs."""
        try:
            if year not in self.alternative_dfs:
                return None

            df = self.alternative_dfs[year]
            data = df[df['NUM_COM'] == str(commune)].copy()

            if data.empty:
                return None

            row = data.iloc[0]
            return {
                year: {
                    "commune_name": row['NOM_COM'],
                    "coverage_rates": {
                        "commune": float(row['tauxcouv_com']),
                        "epci": float(row['tauxcouv_epci']),
                        "department": float(row['tauxcouv_dep']),
                        "region": float(row['tauxcouv_reg']),
                        "france": float(row['tauxcouv_fe'])
                    }
                }
            }
        except Exception as e:
            print(f"Erreur lors de la lecture des données alternatives: {str(e)}")
            return None

    def get_coverage_by_commune(self, commune: str, start_year: int = None, end_year: int = None):
        try:
            # Essayer d'abord avec les données parquet actuelles
            df = self.dfs['commune']
            data = df[df['numcom'] == str(commune)].copy()
            result = {}
            data_source = "current"

            # Si aucune donnée trouvée dans parquet, chercher dans les données alternatives
            if data.empty:
                for year in self.alternative_dfs.keys():
                    if (not start_year or year >= start_year) and (not end_year or year <= end_year):
                        alternative_data = self.get_coverage_from_alternative(commune, year)
                        if alternative_data:
                            result.update(alternative_data)
                            data_source = "alternative"

                if not result:
                    return {"error": "Commune non trouvée dans les données actuelles et alternatives"}

            else:
                if start_year and end_year:
                    data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

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
                "coverage_data": result,
                "data_source": data_source
            }
        except Exception as e:
            return {"error": str(e)}

    def get_coverage_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour un EPCI"""
        try:
            if 'epci' not in self.dfs or self.dfs['epci'].empty:
                return {"error": "Données EPCI non disponibles"}

            df = self.dfs['epci']
            data = df[df['numepci'] == str(epci)]

            if data.empty:
                return {"error": f"EPCI {epci} non trouvé"}

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}

            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "territory_name": row['nomepci'],
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
                "coverage_data": result,
                "data_source": "current"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_epci: {str(e)}")
            return {"error": str(e)}

    def get_coverage_by_department(self, dep: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour un département"""
        try:
            if 'department' not in self.dfs or self.dfs['department'].empty:
                return {"error": "Données départementales non disponibles"}

            df = self.dfs['department']
            data = df[df['numdep'] == str(dep)]

            if data.empty:
                return {"error": f"Département {dep} non trouvé"}

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}

            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "territory_name": row['nomdep'],
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
                "coverage_data": result,
                "data_source": "current"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_department: {str(e)}")
            return {"error": str(e)}

    def get_coverage_by_region(self, reg: str, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour une région"""
        try:
            if 'region' not in self.dfs or self.dfs['region'].empty:
                return {"error": "Données régionales non disponibles"}

            df = self.dfs['region']
            data = df[df['numregi'] == str(reg)]  # Changed from 'reg' to 'numregi'

            if data.empty:
                return {"error": f"Région {reg} non trouvée"}

            if start_year and end_year:
                data = data[(data['annee'] >= start_year) & (data['annee'] <= end_year)]

            result = {}

            for _, row in data.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "territory_name": row['nomregi'],  # Changed from 'nomreg' to 'nomregi'
                    "coverage_rates": {
                        "eaje_psu": float(row['txcouv_psu_col_reg']),  # Changed from 'txcouv_psu_reg'
                        "eaje_hors_psu": float(row['txcouv_hors_psu_col_reg']),
                        "eaje_total": float(row['txcouv_eaje_reg']),
                        "preschool": float(row['txcouv_prescol_reg']),
                        "childminder": float(row['txcouv_am_ind_reg']),  # Changed from 'txcouv_am_reg'
                        "home_care": float(row['txcouv_gad_ind_reg']),  # Changed from 'txcouv_gad_reg'
                        "individual_total": float(row['txcouv_ind_reg']),
                        "global": float(row['txcouv_reg'])
                    }
                }

            return {
                "coverage_data": result,
                "data_source": "current"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_by_region: {str(e)}")
            return {"error": str(e)}


    def get_coverage_france(self, start_year: int = None, end_year: int = None):
        """Récupère les données de couverture pour la France entière"""
        try:
            # Vérifier que nous avons les données pour la France
            if 'france' not in self.dfs or self.dfs['france'].empty:
                return {"error": "Données nationales non disponibles"}

            df = self.dfs['france']

            # Filtrer sur les années si spécifiées
            if start_year and end_year:
                df = df[(df['annee'] >= start_year) & (df['annee'] <= end_year)]

            result = {}

            # Traiter chaque année
            for _, row in df.iterrows():
                year = int(row['annee'])
                result[year] = {
                    "territory_name": row['national'],
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
                "coverage_data": result,
                "data_source": "current"
            }

        except Exception as e:
            print(f"Erreur dans get_coverage_france: {str(e)}")
            return {"error": str(e)}
