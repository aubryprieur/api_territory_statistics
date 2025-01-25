import pandas as pd
from pathlib import Path

class RevenueService:
    def __init__(self):
       self.dfs = {}
       self.dfs_epci = {}
       self.dfs_dep = {}
       self.dfs_reg = {}
       self.dfs_france = {}
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


    def get_median_revenues(self, codgeo: str):
       medians = {}
       for year in range(2017, 2022):
           try:
               median = self.dfs[year][
                   self.dfs[year]["CODGEO"] == codgeo
               ][f"MED{str(year)[2:]}"].iloc[0]
               medians[year] = float(median)
           except (IndexError, KeyError):
               medians[year] = None

       return {
           "commune": codgeo,
           "median_revenues": medians
       }

    def get_median_revenues_epci(self, epci: str):
       try:
           medians = {}
           for year in range(2017, 2022):
               # Conversion du code EPCI en int pour la comparaison
               df_year = self.dfs_epci[year]
               df_year['CODGEO'] = df_year['CODGEO'].astype(str)
               median = df_year[df_year["CODGEO"] == str(epci)][f"MED{str(year)[2:]}"].iloc[0]
               medians[year] = float(median)
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur pour {epci}: {e}")
           medians[year] = None
       return {
           "epci": epci,
           "median_revenues": medians
       }

    def get_median_revenues_department(self, dep: str):
       try:
           medians = {}
           for year in range(2017, 2022):
               df_year = self.dfs_dep[year]
               df_year['CODGEO'] = df_year['CODGEO'].astype(str)
               median = df_year[df_year["CODGEO"] == str(dep)][f"MED{str(year)[2:]}"].iloc[0]
               medians[year] = float(median)
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur pour {dep}: {e}")
           medians[year] = None
       return {
           "department": dep,
           "median_revenues": medians
       }

    def get_median_revenues_region(self, reg: str):
       try:
           medians = {}
           for year in range(2017, 2022):
               df_year = self.dfs_reg[year]
               df_year['CODGEO'] = df_year['CODGEO'].astype(str)
               median = df_year[df_year["CODGEO"] == str(reg)][f"MED{str(year)[2:]}"].iloc[0]
               medians[year] = float(median)
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur pour {reg}: {e}")
           medians[year] = None
       return {
           "region": reg,
           "median_revenues": medians
       }

    def get_median_revenues_france(self):
       try:
           medians = {}
           for year in range(2017, 2022):
               median = self.dfs_france[year][f"MED{str(year)[2:]}"].iloc[0]
               medians[year] = float(median)
       except (IndexError, KeyError, ValueError) as e:
           print(f"Erreur: {e}")
           medians[year] = None
       return {
           "median_revenues": medians
       }
