import pandas as pd
from pathlib import Path

class PopulationService:
   def __init__(self):
       self.df = pd.read_csv(
           Path("data/population/TD_POP1B_2021.csv"),
           delimiter=";",
           encoding="utf-8",
           low_memory=False
       )

   def get_all_data(self):
       return self.df.to_dict(orient="records")

   def get_by_code(self, codgeo: str):
       return self.df[self.df["CODGEO"] == str(codgeo)].to_dict(orient="records")

   def get_population_and_children_rate(self, code: str):
       total_pop = self.df[self.df["CODGEO"] == code]["NB"].sum()
       under_3 = self.df[(self.df["CODGEO"] == code) & (self.df["AGED100"].isin([0, 1, 2]))]["NB"].sum()
       three_to_five = self.df[(self.df["CODGEO"] == code) & (self.df["AGED100"].isin([3, 4, 5]))]["NB"].sum()

       return {
           "total_population": float(total_pop),
           "children_under_3": float(under_3),
           "children_3_to_5": float(three_to_five),
           "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
           "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0
       }

   def aggregate_children_by_epci(self, epci: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["EPCI"] == epci]["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       under_3 = pop_data[pop_data["AGED100"].isin([0, 1, 2])]["NB"].sum()
       three_to_five = pop_data[pop_data["AGED100"].isin([3, 4, 5])]["NB"].sum()
       total_pop = float(pop_data["NB"].sum())

       return {
           "epci": epci,
           "epci_name": geocode_service.df[geocode_service.df["EPCI"] == epci]["LIBEPCI"].iloc[0],
           "total_population": total_pop,
           "children_under_3": float(under_3),
           "children_3_to_5": float(three_to_five),
           "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
           "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes)
       }

   def aggregate_children_by_department(self, dep: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["DEP"] == dep]["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       under_3 = pop_data[pop_data["AGED100"].isin([0, 1, 2])]["NB"].sum()
       three_to_five = pop_data[pop_data["AGED100"].isin([3, 4, 5])]["NB"].sum()
       total_pop = float(pop_data["NB"].sum())

       return {
           "department": dep,
           "total_population": total_pop,
           "children_under_3": float(under_3),
           "children_3_to_5": float(three_to_five),
           "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
           "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes)
       }

   def aggregate_children_by_region(self, reg: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["REG"] == float(reg)]["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       under_3 = pop_data[pop_data["AGED100"].isin([0, 1, 2])]["NB"].sum()
       three_to_five = pop_data[pop_data["AGED100"].isin([3, 4, 5])]["NB"].sum()
       total_pop = float(pop_data["NB"].sum())
       departments = geocode_service.df[geocode_service.df["REG"] == float(reg)]["DEP"].unique()

       return {
           "region": reg,
           "total_population": total_pop,
           "children_under_3": float(under_3),
           "children_3_to_5": float(three_to_five),
           "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
           "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes),
           "departments_count": len(departments)
       }

   def aggregate_children_france(self, geocode_service):
       communes = geocode_service.df["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       under_3 = pop_data[pop_data["AGED100"].isin([0, 1, 2])]["NB"].sum()
       three_to_five = pop_data[pop_data["AGED100"].isin([3, 4, 5])]["NB"].sum()
       total_pop = float(pop_data["NB"].sum())

       return {
           "total_population": total_pop,
           "children_under_3": float(under_3),
           "children_3_to_5": float(three_to_five),
           "under_3_rate": float(under_3/total_pop * 100) if total_pop > 0 else 0,
           "three_to_five_rate": float(three_to_five/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes),
           "departments_count": len(geocode_service.df["DEP"].unique()),
           "regions_count": len(geocode_service.df["REG"].unique())
       }
