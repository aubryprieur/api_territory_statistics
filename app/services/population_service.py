import pandas as pd
from pathlib import Path

class PopulationService:
    def __init__(self):
        self.df = pd.read_csv(
            Path("data/TD_POP1B_2021.csv"),
            delimiter=";",
            encoding="utf-8",
            low_memory=False
        )

    def get_all_data(self):
        return self.df.to_dict(orient="records")

    def get_by_code(self, codgeo: str):
        return self.df[self.df["CODGEO"] == str(codgeo)].to_dict(orient="records")

    def get_children_under_3(self, code: str):
        try:
            result = self.df[
                (self.df["CODGEO"] == code) &
                (self.df["AGED100"].isin([0, 1, 2]))
            ]
            return float(result["NB"].sum())
        except ValueError:
            return 0

    def aggregate_children_by_epci(self, epci: str, geocode_service):
        communes = geocode_service.df[geocode_service.df["EPCI"] == epci]["CODGEO"].tolist()
        total = sum(self.get_children_under_3(commune) for commune in communes)
        return {
            "epci": epci,
            "total_children_under_3": total,
            "communes_count": len(communes)
        }

    def aggregate_children_by_epci(self, epci: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["EPCI"] == epci]["CODGEO"].tolist()
       children_data = self.df[
           (self.df["CODGEO"].isin(communes)) &
           (self.df["AGED100"].isin([0, 1, 2]))
       ]
       total = float(children_data["NB"].sum())

       return {
           "epci": epci,
           "epci_name": geocode_service.df[geocode_service.df["EPCI"] == epci]["LIBEPCI"].iloc[0],
           "total_children_under_3": total,
           "communes_count": len(communes),
           "details": {
               "age_0": float(children_data[children_data["AGED100"] == 0]["NB"].sum()),
               "age_1": float(children_data[children_data["AGED100"] == 1]["NB"].sum()),
               "age_2": float(children_data[children_data["AGED100"] == 2]["NB"].sum())
           }
       }

    def aggregate_children_by_department(self, dep: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["DEP"] == dep]["CODGEO"].tolist()
       total = sum(self.get_children_under_3(commune) for commune in communes)
       return {
           "department": dep,
           "total_children_under_3": total,
           "communes_count": len(communes)
       }

    def aggregate_children_by_region(self, reg: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["REG"] == float(reg)]["CODGEO"].tolist()
       total = sum(self.get_children_under_3(commune) for commune in communes)
       departments = geocode_service.df[geocode_service.df["REG"] == float(reg)]["DEP"].unique()
       return {
           "region": reg,
           "total_children_under_3": total,
           "communes_count": len(communes),
           "departments_count": len(departments)
       }

    def aggregate_children_france(self, geocode_service):
       communes = geocode_service.df["CODGEO"].tolist()
       total = sum(self.get_children_under_3(commune) for commune in communes)
       return {
           "total_children_under_3": total,
           "communes_count": len(communes),
           "departments_count": len(geocode_service.df["DEP"].unique()),
           "regions_count": len(geocode_service.df["REG"].unique())
       }

    def get_population_and_children_rate(self, code: str):
       total_pop = self.df[self.df["CODGEO"] == code]["NB"].sum()
       children = self.get_children_under_3(code)
       return {
           "total_population": float(total_pop),
           "children_under_3": float(children),
           "children_rate": float(children/total_pop * 100) if total_pop > 0 else 0
       }

    def aggregate_children_by_epci(self, epci: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["EPCI"] == epci]["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       children_data = pop_data[pop_data["AGED100"].isin([0, 1, 2])]

       total_pop = float(pop_data["NB"].sum())
       total_children = float(children_data["NB"].sum())

       return {
           "epci": epci,
           "epci_name": geocode_service.df[geocode_service.df["EPCI"] == epci]["LIBEPCI"].iloc[0],
           "total_population": total_pop,
           "total_children_under_3": total_children,
           "children_rate": float(total_children/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes)
       }

    def aggregate_children_by_department(self, dep: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["DEP"] == dep]["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       children_data = pop_data[pop_data["AGED100"].isin([0, 1, 2])]

       total_pop = float(pop_data["NB"].sum())
       total_children = float(children_data["NB"].sum())

       return {
           "department": dep,
           "total_population": total_pop,
           "total_children_under_3": total_children,
           "children_rate": float(total_children/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes)
       }

    def aggregate_children_by_region(self, reg: str, geocode_service):
       communes = geocode_service.df[geocode_service.df["REG"] == float(reg)]["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       children_data = pop_data[pop_data["AGED100"].isin([0, 1, 2])]

       total_pop = float(pop_data["NB"].sum())
       total_children = float(children_data["NB"].sum())
       departments = geocode_service.df[geocode_service.df["REG"] == float(reg)]["DEP"].unique()

       return {
           "region": reg,
           "total_population": total_pop,
           "total_children_under_3": total_children,
           "children_rate": float(total_children/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes),
           "departments_count": len(departments)
       }

    def aggregate_children_france(self, geocode_service):
       communes = geocode_service.df["CODGEO"].tolist()
       pop_data = self.df[self.df["CODGEO"].isin(communes)]
       children_data = pop_data[pop_data["AGED100"].isin([0, 1, 2])]

       total_pop = float(pop_data["NB"].sum())
       total_children = float(children_data["NB"].sum())

       return {
           "total_population": total_pop,
           "total_children_under_3": total_children,
           "children_rate": float(total_children/total_pop * 100) if total_pop > 0 else 0,
           "communes_count": len(communes),
           "departments_count": len(geocode_service.df["DEP"].unique()),
           "regions_count": len(geocode_service.df["REG"].unique())
       }
