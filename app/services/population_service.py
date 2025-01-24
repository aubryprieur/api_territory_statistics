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
