import pandas as pd
from pathlib import Path

class GeoCodeService:
   def __init__(self):
       self.df = pd.read_csv(
           Path("data/COG_au_01-01-2024.csv"),
           delimiter=";",
           encoding="utf-8",
           low_memory=False
       )

   def get_by_code(self, code: str):
       return self.df[self.df["CODGEO"] == code].to_dict(orient="records")

   def get_by_region(self, reg: str):
       return self.df[self.df["REG"] == float(reg)].to_dict(orient="records")

   def get_by_department(self, dep: str):
       return self.df[self.df["DEP"] == dep].to_dict(orient="records")

   def aggregate_births_by_epci(self, epci: str, birth_service):
       try:
           communes = self.df[self.df["EPCI"] == epci]["CODGEO"].tolist()
           births_df = birth_service.df[
               (birth_service.df["GEO"].isin(communes)) &
               (birth_service.df["GEO_OBJECT"] == "COM")
           ]

           yearly_births = births_df.groupby("TIME_PERIOD")["OBS_VALUE"].sum()

           return {
               "epci": epci,
               "epci_name": self.df[self.df["EPCI"] == epci]["LIBEPCI"].iloc[0] if len(communes) > 0 else "",
               "total_births": float(births_df["OBS_VALUE"].sum()),
               "communes_count": int(len(communes)),
               "births_by_year": {int(k): float(v) for k,v in yearly_births.to_dict().items()}
           }
       except IndexError:
           return {"error": "EPCI non trouvé"}

   def aggregate_births_by_department(self, dep: str, birth_service):
       communes = self.df[self.df["DEP"] == dep]["CODGEO"].tolist()
       births_df = birth_service.df[
           (birth_service.df["GEO"].isin(communes)) &
           (birth_service.df["GEO_OBJECT"] == "COM")
       ]
       return {
           "department": dep,
           "total_births": float(births_df["OBS_VALUE"].sum()),
           "communes_count": int(len(communes)),
           "births_by_year": {int(k): float(v) for k,v in births_df.groupby("TIME_PERIOD")["OBS_VALUE"].sum().to_dict().items()}
       }

   def aggregate_births_by_region(self, reg: str, birth_service):
       communes = self.df[self.df["REG"] == float(reg)]["CODGEO"].tolist()
       births_df = birth_service.df[
           (birth_service.df["GEO"].isin(communes)) &
           (birth_service.df["GEO_OBJECT"] == "COM")
       ]
       departments = self.df[self.df["REG"] == float(reg)]["DEP"].unique().tolist()
       return {
           "region": reg,
           "total_births": float(births_df["OBS_VALUE"].sum()),
           "communes_count": int(len(communes)),
           "departments_count": len(departments),
           "births_by_year": {int(k): float(v) for k,v in births_df.groupby("TIME_PERIOD")["OBS_VALUE"].sum().to_dict().items()}
       }

   def aggregate_births_france(self, birth_service):
       births_df = birth_service.df[birth_service.df["GEO_OBJECT"] == "COM"]
       return {
           "total_births": float(births_df["OBS_VALUE"].sum()),
           "communes_count": len(self.df),
           "departments_count": len(self.df["DEP"].unique()),
           "regions_count": len(self.df["REG"].unique()),
           "births_by_year": {int(k): float(v) for k,v in births_df.groupby("TIME_PERIOD")["OBS_VALUE"].sum().to_dict().items()}
       }

   def get_region_hierarchy(self, reg: str):
       region_data = self.df[self.df["REG"] == float(reg)]
       return {
           "region": reg,
           "departments": region_data["DEP"].unique().tolist(),
           "communes": region_data["CODGEO"].tolist()
       }
