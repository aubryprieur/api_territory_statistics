import pandas as pd
from pathlib import Path

class FamilyService:
    def __init__(self):
       self.dfs = {}
       for year in range(2017, 2022):
           self.dfs[year] = pd.read_csv(
               Path(f"data/families/commune/base-cc-coupl-fam-men-{year}.CSV"),
               delimiter=";",
               encoding="utf-8",
               low_memory=False
           )

    def _calculate_percentages(self, total, couples_children, single_parent, single_father, single_mother, couples_no_children):
       return {
           "total_families": total,
           "couples_with_children": {
               "count": couples_children,
               "percentage": round((couples_children / total * 100), 1) if total > 0 else 0
           },
           "single_parent": {
               "count": single_parent,
               "percentage": round((single_parent / total * 100), 1) if total > 0 else 0
           },
           "single_father": {
               "count": single_father,
               "percentage": round((single_father / total * 100), 1) if total > 0 else 0
           },
           "single_mother": {
               "count": single_mother,
               "percentage": round((single_mother / total * 100), 1) if total > 0 else 0
           },
           "couples_without_children": {
               "count": couples_no_children,
               "percentage": round((couples_no_children / total * 100), 1) if total > 0 else 0
           }
       }

    def _calculate_evolution(self, data):
     # Get first and last year from available data
     years = sorted(data.keys())
     start_year = years[0]
     end_year = years[-1]

     evolutions = {}
     metrics = [
         "total_families",
         "couples_with_children",
         "single_parent",
         "single_father",
         "single_mother",
         "couples_without_children"
     ]

     for metric in metrics:
         if metric == "total_families":
             value_start = data[start_year][metric]
             value_end = data[end_year][metric]
         else:
             value_start = data[start_year][metric]["count"]
             value_end = data[end_year][metric]["count"]

         evolution = round(((value_end - value_start) / value_start * 100), 1) if value_start > 0 else 0
         evolutions[metric] = {
             "start_value": value_start,
             "end_value": value_end,
             "evolution_percentage": evolution,
             "period": f"{start_year}-{end_year}"
         }

     return evolutions

    # Modifier chaque méthode pour inclure l'évolution :

    def get_families_by_commune(self, code: str):
     try:
         data = self._get_data_for_commune(code)
         evolutions = self._calculate_evolution(data)
         return {
             "commune": code,
             "family_data": data,
             "evolution": evolutions
         }
     except Exception as e:
         return {"error": str(e)}

    def get_families_by_epci(self, epci: str, geocode_service):
     try:
         data = self._get_data_for_epci(epci, geocode_service)
         evolutions = self._calculate_evolution(data)
         return {
             "epci": epci,
             "family_data": data,
             "evolution": evolutions
         }
     except Exception as e:
         return {"error": str(e)}

    def get_families_by_department(self, dep: str, geocode_service):
     try:
         data = self._get_data_for_department(dep, geocode_service)
         evolutions = self._calculate_evolution(data)
         return {
             "department": dep,
             "family_data": data,
             "evolution": evolutions
         }
     except Exception as e:
         return {"error": str(e)}

    def get_families_by_region(self, reg: str, geocode_service):
     try:
         data = self._get_data_for_region(reg, geocode_service)
         evolutions = self._calculate_evolution(data)
         return {
             "region": reg,
             "family_data": data,
             "evolution": evolutions
         }
     except Exception as e:
         return {"error": str(e)}

    def get_families_france(self):
     try:
         data = self._get_data_for_france()
         evolutions = self._calculate_evolution(data)
         return {
             "family_data": data,
             "evolution": evolutions
         }
     except Exception as e:
         return {"error": str(e)}

    # Méthodes helpers pour extraire les données par niveau géographique

    def _get_data_for_commune(self, code: str):
     data = {}
     for year in sorted(self.dfs.keys()):
         suffix = str(year)[2:]
         commune_data = self.dfs[year][self.dfs[year]["CODGEO"] == str(code)]
         if not commune_data.empty:
             data[year] = self._extract_year_data(commune_data, suffix)
     return data

    def _get_data_for_epci(self, epci: str, geocode_service):
     data = {}
     for year in sorted(self.dfs.keys()):
         suffix = str(year)[2:]
         communes = geocode_service.df[geocode_service.df["EPCI"] == epci]["CODGEO"].tolist()
         epci_data = self.dfs[year][self.dfs[year]["CODGEO"].isin(communes)]
         data[year] = self._extract_year_data(epci_data, suffix, sum_data=True)
     return data

    def _get_data_for_department(self, dep: str, geocode_service):
     data = {}
     for year in sorted(self.dfs.keys()):
         suffix = str(year)[2:]
         communes = geocode_service.df[geocode_service.df["DEP"] == dep]["CODGEO"].tolist()
         dep_data = self.dfs[year][self.dfs[year]["CODGEO"].isin(communes)]
         data[year] = self._extract_year_data(dep_data, suffix, sum_data=True)
     return data

    def _get_data_for_region(self, reg: str, geocode_service):
     data = {}
     for year in sorted(self.dfs.keys()):
         suffix = str(year)[2:]
         communes = geocode_service.df[geocode_service.df["REG"] == float(reg)]["CODGEO"].tolist()
         reg_data = self.dfs[year][self.dfs[year]["CODGEO"].isin(communes)]
         data[year] = self._extract_year_data(reg_data, suffix, sum_data=True)
     return data

    def _get_data_for_france(self):
     data = {}
     for year in sorted(self.dfs.keys()):
         suffix = str(year)[2:]
         data[year] = self._extract_year_data(self.dfs[year], suffix, sum_data=True)
     return data

    def _extract_year_data(self, df, suffix, sum_data=False):
     if sum_data:
         total_families = float(df[f"C{suffix}_FAM"].sum())
         couples_with_children = float(df[f"C{suffix}_COUPAENF"].sum())
         single_parent = float(df[f"C{suffix}_FAMMONO"].sum())
         single_father = float(df[f"C{suffix}_HMONO"].sum())
         single_mother = float(df[f"C{suffix}_FMONO"].sum())
         couples_without_children = float(df[f"C{suffix}_COUPSENF"].sum())
     else:
         total_families = float(df[f"C{suffix}_FAM"].iloc[0])
         couples_with_children = float(df[f"C{suffix}_COUPAENF"].iloc[0])
         single_parent = float(df[f"C{suffix}_FAMMONO"].iloc[0])
         single_father = float(df[f"C{suffix}_HMONO"].iloc[0])
         single_mother = float(df[f"C{suffix}_FMONO"].iloc[0])
         couples_without_children = float(df[f"C{suffix}_COUPSENF"].iloc[0])

     return self._calculate_percentages(
         total_families, couples_with_children, single_parent,
         single_father, single_mother, couples_without_children
     )
