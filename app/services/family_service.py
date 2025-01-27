import pandas as pd
from pathlib import Path

class FamilyService:
    def __init__(self):
        self.dfs = {}
        self.dfs_iris = {}
        # Charger les données communes
        for year in range(2010, 2022):
            try:
                self.dfs[year] = pd.read_csv(
                    Path(f"data/families/commune/base-cc-coupl-fam-men-{year}.CSV"),
                    delimiter=";",
                    encoding="utf-8",
                    low_memory=False
                )
            except FileNotFoundError:
                continue

        # Charger les données IRIS (2017-2021)
        for year in range(2017, 2022):
            try:
                self.dfs_iris[year] = pd.read_csv(
                    Path(f"data/families/iris/base-ic-couples-familles-menages-{year}.CSV"),
                    delimiter=";",
                    encoding="utf-8",
                    low_memory=False
                )
            except FileNotFoundError:
                continue

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

    def _calculate_evolution(self, data, start_year=None, end_year=None):
       years = sorted(data.keys())
       start_year = start_year or years[0]
       end_year = end_year or years[-1]

       if start_year not in years or end_year not in years:
           return {"error": f"Years must be between {years[0]} and {years[-1]}"}

       evolutions = {}
       metrics = ["total_families", "couples_with_children", "single_parent",
                 "single_father", "single_mother", "couples_without_children"]

       for metric in metrics:
           value_start = data[start_year][metric]["count"] if metric != "total_families" else data[start_year][metric]
           value_end = data[end_year][metric]["count"] if metric != "total_families" else data[end_year][metric]

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

    def get_iris_families_by_commune(self, commune: str, geocode_service):
        try:
            iris_codes = set(geocode_service.iris_geo[geocode_service.iris_geo["DEPCOM"] == str(commune)]["CODE_IRIS"])
            data = {}

            for year in range(2017, 2022):
                suffix = str(year)[2:]
                iris_df = self.dfs_iris[year]
                commune_data = iris_df[iris_df["COM"] == str(commune)]
                iris_data = {}

                for iris in iris_codes:
                    iris_row = commune_data[commune_data["IRIS"] == iris]
                    if not iris_row.empty:
                        total_families = float(iris_row[f"C{suffix}_FAM"].iloc[0])
                        couples_with_children = float(iris_row[f"C{suffix}_COUPAENF"].iloc[0])
                        single_parent = float(iris_row[f"C{suffix}_FAMMONO"].iloc[0])
                        couples_without_children = float(iris_row[f"C{suffix}_COUPSENF"].iloc[0])
                        iris_name = geocode_service.iris_geo[
                            geocode_service.iris_geo["CODE_IRIS"] == iris
                        ]["LIB_IRIS"].iloc[0]
                        iris_data[iris] = {
                            "iris_name": iris_name,
                            "data": {
                                "total_families": total_families,
                                "couples_with_children": {
                                    "count": couples_with_children,
                                    "percentage": round((couples_with_children / total_families * 100), 1) if total_families > 0 else 0
                                },
                                "single_parent": {
                                    "count": single_parent,
                                    "percentage": round((single_parent / total_families * 100), 1) if total_families > 0 else 0
                                },
                                "couples_without_children": {
                                    "count": couples_without_children,
                                    "percentage": round((couples_without_children / total_families * 100), 1) if total_families > 0 else 0
                                }
                            }
                        }
                if iris_data:
                    data[year] = iris_data

            evolutions = {}
            for iris in iris_codes:
                try:
                    yearly_data = {
                        year: data[year][iris]["data"]
                        for year in data.keys()
                        if iris in data[year]
                    }
                    if yearly_data:
                        metrics = ["total_families", "couples_with_children", "single_parent", "couples_without_children"]
                        evolution_data = {}
                        start_year = min(yearly_data.keys())
                        end_year = max(yearly_data.keys())

                        for metric in metrics:
                            if metric == "total_families":
                                start_value = yearly_data[start_year][metric]
                                end_value = yearly_data[end_year][metric]
                            else:
                                start_value = yearly_data[start_year][metric]["count"]
                                end_value = yearly_data[end_year][metric]["count"]

                            evolution = round(((end_value - start_value) / start_value * 100), 1) if start_value > 0 else 0
                            evolution_data[metric] = {
                                "start_value": start_value,
                                "end_value": end_value,
                                "evolution_percentage": evolution,
                                "period": f"{start_year}-{end_year}"
                            }

                        evolutions[iris] = evolution_data
                except Exception as e:
                    print(f"Erreur évolution pour IRIS {iris}: {str(e)}")
                    continue

            return {
                "commune": commune,
                "iris_count": len(iris_codes),
                "iris_data": data,
                "evolution": evolutions
            }
        except Exception as e:
            print(f"Erreur détaillée: {str(e)}")
            return {"error": str(e)}
