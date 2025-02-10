import pandas as pd
from pathlib import Path

class RevenueService:
    def __init__(self):
       self.dfs = {}
       self.dfs_epci = {}
       self.dfs_dep = {}
       self.dfs_reg = {}
       self.dfs_france = {}
       self.dfs_iris = {}

       for year in range(2017, 2022):
           self.dfs[year] = pd.read_csv(
               Path(f"data/revenues/commune/cc_filosofi_{year}_COM.csv"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )
           self.dfs_epci[year] = pd.read_csv(
               Path(f"data/revenues/epci/cc_filosofi_{year}_EPCI.csv"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )
           self.dfs_dep[year] = pd.read_csv(
               Path(f"data/revenues/department/cc_filosofi_{year}_DEP.csv"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )
           self.dfs_reg[year] = pd.read_csv(
               Path(f"data/revenues/region/cc_filosofi_{year}_REG.csv"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )
           self.dfs_france[year] = pd.read_csv(
               Path(f"data/revenues/france/cc_filosofi_{year}_METRO.csv"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )
           self.dfs_iris[year] = pd.read_csv(
               Path(f"data/revenues/iris/BASE_TD_FILO_DISP_IRIS_{year}.csv"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )

    def _convert_to_float(self, value):
        """Convertit une valeur en float, gère les nombres avec virgule"""
        if pd.isna(value):
            return None
        if isinstance(value, str):
            return float(value.replace(',', '.'))
        return float(value)

    def get_median_revenues(self, codgeo: str):
       medians = {}
       poverty_rates = {}
       for year in range(2017, 2022):
           try:
               df_year = self.dfs[year]
               row = df_year[df_year["CODGEO"] == codgeo]
               if not row.empty:
                   medians[year] = self._convert_to_float(row[f"MED{str(year)[2:]}"].iloc[0])
                   poverty_rates[year] = self._convert_to_float(row[f"TP60{str(year)[2:]}"].iloc[0])
               else:
                   medians[year] = None
                   poverty_rates[year] = None
           except (IndexError, KeyError):
               medians[year] = None
               poverty_rates[year] = None
       return {
           "commune": codgeo,
           "median_revenues": medians,
           "poverty_rates": poverty_rates
       }

    def get_median_revenues_epci(self, epci: str):
       medians = {}
       poverty_rates = {}
       try:
           for year in range(2017, 2022):
               df_year = self.dfs_epci[year]
               df_year['CODGEO'] = df_year['CODGEO'].astype(str)
               row = df_year[df_year["CODGEO"] == str(epci)]
               if not row.empty:
                   medians[year] = self._convert_to_float(row[f"MED{str(year)[2:]}"].iloc[0])
                   poverty_rates[year] = self._convert_to_float(row[f"TP60{str(year)[2:]}"].iloc[0])
               else:
                   medians[year] = None
                   poverty_rates[year] = None
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur pour {epci}: {e}")
           medians[year] = None
           poverty_rates[year] = None
       return {
           "epci": epci,
           "median_revenues": medians,
           "poverty_rates": poverty_rates
       }

    def get_median_revenues_department(self, dep: str):
       medians = {}
       poverty_rates = {}
       try:
           for year in range(2017, 2022):
               df_year = self.dfs_dep[year]
               df_year['CODGEO'] = df_year['CODGEO'].astype(str)
               row = df_year[df_year["CODGEO"] == str(dep)]
               if not row.empty:
                   medians[year] = self._convert_to_float(row[f"MED{str(year)[2:]}"].iloc[0])
                   poverty_rates[year] = self._convert_to_float(row[f"TP60{str(year)[2:]}"].iloc[0])
               else:
                   medians[year] = None
                   poverty_rates[year] = None
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur pour {dep}: {e}")
           medians[year] = None
           poverty_rates[year] = None
       return {
           "department": dep,
           "median_revenues": medians,
           "poverty_rates": poverty_rates
       }

    def get_median_revenues_region(self, reg: str):
       medians = {}
       poverty_rates = {}
       try:
           for year in range(2017, 2022):
               df_year = self.dfs_reg[year]
               df_year['CODGEO'] = df_year['CODGEO'].astype(str)
               row = df_year[df_year["CODGEO"] == str(reg)]
               if not row.empty:
                   medians[year] = self._convert_to_float(row[f"MED{str(year)[2:]}"].iloc[0])
                   poverty_rates[year] = self._convert_to_float(row[f"TP60{str(year)[2:]}"].iloc[0])
               else:
                   medians[year] = None
                   poverty_rates[year] = None
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur pour {reg}: {e}")
           medians[year] = None
           poverty_rates[year] = None
       return {
           "region": reg,
           "median_revenues": medians,
           "poverty_rates": poverty_rates
       }

    def get_median_revenues_france(self):
       medians = {}
       poverty_rates = {}
       try:
           for year in range(2017, 2022):
               df_year = self.dfs_france[year]
               if not df_year.empty:
                   medians[year] = self._convert_to_float(df_year[f"MED{str(year)[2:]}"].iloc[0])
                   poverty_rates[year] = self._convert_to_float(df_year[f"TP60{str(year)[2:]}"].iloc[0])
               else:
                   medians[year] = None
                   poverty_rates[year] = None
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur: {e}")
           medians[year] = None
           poverty_rates[year] = None
       return {
           "median_revenues": medians,
           "poverty_rates": poverty_rates
       }

    def get_iris_revenues_by_commune(self, commune: str, geocode_service):
        try:
            # Vérifie si la commune existe dans les données IRIS
            iris_data = geocode_service.iris_geo[geocode_service.iris_geo["DEPCOM"] == str(commune)]
            if iris_data.empty:
                return {"error": f"Aucun IRIS trouvé pour la commune {commune}"}

            results = {}

            for year in range(2017, 2022):
                year_data = []
                if year not in self.dfs_iris:
                    continue

                iris_df = self.dfs_iris[year]
                year_suffix = str(year)[2:]

                # Construction des noms de colonnes pour l'année avec le préfixe DISP_
                median_col = f"DISP_MED{year_suffix}"
                poverty_col = f"DISP_TP60{year_suffix}"  # Ajout du préfixe DISP_

                # Vérifie si les colonnes existent
                if median_col not in iris_df.columns or poverty_col not in iris_df.columns:
                    print(f"Colonnes manquantes pour l'année {year}. Recherchées : {median_col}, {poverty_col}")
                    print(f"Colonnes disponibles : {iris_df.columns.tolist()}")
                    continue

                for iris_code in iris_data["CODE_IRIS"]:
                    try:
                        row = iris_df[iris_df["IRIS"] == iris_code]
                        if not row.empty:
                            median = self._convert_to_float(row[median_col].values[0])
                            poverty_rate = self._convert_to_float(row[poverty_col].values[0])

                            if median is not None and poverty_rate is not None:
                                iris_name = iris_data[iris_data["CODE_IRIS"] == iris_code]["LIB_IRIS"].values[0]
                                year_data.append({
                                    "iris_code": iris_code,
                                    "iris_name": iris_name,
                                    "median": median,
                                    "poverty_rate": poverty_rate
                                })
                    except (IndexError, ValueError) as e:
                        print(f"Erreur pour IRIS {iris_code}, année {year}: {str(e)}")
                        continue

                if year_data:  # N'ajoute l'année que si on a des données
                    results[year] = year_data

            if not results:
                return {"error": f"Aucune donnée de revenu trouvée pour la commune {commune}"}

            return {
                "commune": commune,
                "iris_count": len(iris_data),
                "iris_data": results
            }
        except Exception as e:
            print(f"Erreur détaillée dans get_iris_revenues_by_commune: {str(e)}")
            return {"error": str(e)}
