import pandas as pd
from pathlib import Path

class BirthService:
   def __init__(self):
       self.df = pd.read_csv(
           Path("data/births/DS_ETAT_CIVIL_NAIS_COMMUNES_data.csv"),
           delimiter=";",
           encoding="utf-8",
           low_memory=False
       )

   def get_all_data(self):
       return self.df.to_dict(orient="records")

   def get_by_code(self, geo: str):
       try:
           formatted_geo = str(int(geo))
           result = self.df[
               (self.df["GEO"] == formatted_geo) &
               (self.df["GEO_OBJECT"] == "COM")
           ]
           result = result.sort_values("TIME_PERIOD")
           return result.to_dict(orient="records")
       except ValueError:
           return []

   def get_by_year(self, year: int):
       return self.df[self.df["TIME_PERIOD"] == year].to_dict(orient="records")

   def get_stats(self):
       return {
           "total_births": self.df["OBS_VALUE"].sum(),
           "avg_births_per_year": self.df.groupby("TIME_PERIOD")["OBS_VALUE"].mean().to_dict(),
           "communes_count": self.df["GEO"].nunique(),
           "year_range": {
               "min": int(self.df["TIME_PERIOD"].min()),
               "max": int(self.df["TIME_PERIOD"].max())
           }
       }

   def get_filtered_data(self, geo: str = None, geo_object: str = None):
       result = self.df
       if geo:
           try:
               formatted_geo = str(int(geo))
               result = result[result["GEO"] == formatted_geo]
           except ValueError:
               return []
       if geo_object:
           result = result[result["GEO_OBJECT"] == geo_object]
       return result.to_dict(orient="records")

   def get_by_type(self, geo_object: str):
       return self.df[self.df["GEO_OBJECT"] == geo_object].to_dict(orient="records")

   def get_births_trend(self, geo: str):
       try:
           formatted_geo = str(int(geo))
           commune_data = self.df[self.df["GEO"] == formatted_geo]
           return commune_data.groupby("TIME_PERIOD")["OBS_VALUE"].sum().to_dict()
       except ValueError:
           return {}
