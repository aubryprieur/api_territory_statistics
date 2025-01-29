import pandas as pd
from pathlib import Path

class LargeFamilyService:
    def __init__(self):
        self.dfs = {}
        # Charger les données pour chaque année
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

    def _calculate_large_families_data(self, df, year_suffix):
        """Calcule les statistiques des familles nombreuses pour une année donnée"""
        total_families = df[f"C{year_suffix}_FAM"].sum()
        families_3_children = df[f"C{year_suffix}_NE24F3"].sum()
        families_4_plus_children = df[f"C{year_suffix}_NE24F4P"].sum()
        total_large_families = families_3_children + families_4_plus_children

        percentage = (total_large_families / total_families * 100) if total_families > 0 else 0

        return {
            "total_families": float(total_families),
            "families_with_3_children": float(families_3_children),
            "families_with_4_plus_children": float(families_4_plus_children),
            "total_large_families": float(total_large_families),
            "large_families_percentage": round(float(percentage), 1)
        }

    def get_large_families_by_commune(self, code: str):
        """Récupère les données des familles nombreuses pour une commune"""
        data = {}
        for year in sorted(self.dfs.keys()):
            year_suffix = str(year)[2:]
            commune_data = self.dfs[year][self.dfs[year]["CODGEO"] == str(code)]
            if not commune_data.empty:
                data[year] = self._calculate_large_families_data(commune_data, year_suffix)
        return {
            "commune": code,
            "large_families_data": data
        }

    def get_large_families_by_epci(self, epci: str, geocode_service):
        """Récupère les données des familles nombreuses pour un EPCI"""
        data = {}
        for year in sorted(self.dfs.keys()):
            try:
                year_suffix = str(year)[2:]
                communes = geocode_service.df[geocode_service.df["EPCI"] == epci]["CODGEO"].tolist()
                epci_data = self.dfs[year][self.dfs[year]["CODGEO"].isin(communes)]
                if not epci_data.empty:
                    data[year] = self._calculate_large_families_data(epci_data, year_suffix)
            except KeyError:
                continue
        return {
            "epci": epci,
            "large_families_data": data
        }

    def get_large_families_by_department(self, dep: str, geocode_service):
        """Récupère les données des familles nombreuses pour un département"""
        data = {}
        for year in sorted(self.dfs.keys()):
            year_suffix = str(year)[2:]
            communes = geocode_service.df[geocode_service.df["DEP"] == dep]["CODGEO"].tolist()
            dep_data = self.dfs[year][self.dfs[year]["CODGEO"].isin(communes)]
            if not dep_data.empty:
                data[year] = self._calculate_large_families_data(dep_data, year_suffix)
        return {
            "department": dep,
            "large_families_data": data
        }

    def get_large_families_by_region(self, reg: str, geocode_service):
        """Récupère les données des familles nombreuses pour une région"""
        data = {}
        for year in sorted(self.dfs.keys()):
            year_suffix = str(year)[2:]
            communes = geocode_service.df[geocode_service.df["REG"] == float(reg)]["CODGEO"].tolist()
            reg_data = self.dfs[year][self.dfs[year]["CODGEO"].isin(communes)]
            if not reg_data.empty:
                data[year] = self._calculate_large_families_data(reg_data, year_suffix)
        return {
            "region": reg,
            "large_families_data": data
        }

    def get_large_families_france(self):
        """Récupère les données des familles nombreuses pour la France entière"""
        data = {}
        for year in sorted(self.dfs.keys()):
            year_suffix = str(year)[2:]
            national_data = self.dfs[year]
            if not national_data.empty:
                data[year] = self._calculate_large_families_data(national_data, year_suffix)
        return {
            "large_families_data": data
        }
