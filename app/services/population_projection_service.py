"""
Projections démographiques par commune (table population_projection, scripts/import_population_projection.py).
Méthode des composantes par cohortes simplifiée, de 2023 à 2033 : voir le docstring du script d'import.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import PopulationProjection

GROUPS = {"0_2": "Moins de 3 ans", "3_5": "3-5 ans", "6_10": "6-10 ans", "11_14": "11-14 ans", "15_17": "15-17 ans",
          "18_24": "18-24 ans", "60_74": "60-74 ans", "75_84": "75-84 ans", "85p": "85 ans ou plus",
          "total": "Population totale"}
# Fiabilité à 10 ans : dépend surtout de la part des personnes déjà nées et des migrations
RELIABILITY = {"births": "moyenne", "0_2": "moyenne", "3_5": "moyenne", "6_10": "bonne", "11_14": "bonne",
               "15_17": "bonne", "18_24": "moyenne", "60_74": "bonne", "75_84": "bonne", "85p": "bonne",
               "total": "bonne"}
SOURCE = ("Calcul à partir des recensements 2017, 2022 et 2023 (Insee), de l'état civil (naissances domiciliées "
          "2014-2023) et de la table de mortalité de l'Insee (France métropolitaine)")
METHOD = ("Projection par cohortes : chaque année, la population vieillit d'un an, les décès sont appliqués selon la "
          "table de mortalité nationale, les arrivées et départs selon le profil par âge observé dans la commune entre "
          "les recensements 2017 et 2022 (rapproché du département pour les petits effectifs), et les naissances selon "
          "le taux de natalité de la commune (naissances 2021-2023 rapportées aux femmes de 15 à 49 ans), appliqué aux "
          "femmes de 15 à 49 ans projetées. Point de départ : 1er janvier 2023, recalé sur le recensement 2023.")


class PopulationProjectionService:
    def by_commune(self, code):
        code = str(code).zfill(5)
        db = SessionLocal()
        try:
            row = db.query(PopulationProjection).filter(PopulationProjection.geo_code == code).first()
            if row is None:
                return {"error": f"Aucune projection pour la commune {code}"}
            return {"territory": {"level": "COM", "code": code}, "base_year": row.base_year,
                    "population": row.population, "labels": GROUPS, "reliability": RELIABILITY,
                    "source": SOURCE, "method": METHOD, **row.data}
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()
