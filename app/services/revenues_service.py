"""
Revenus et pauvreté — INSEE, Filosofi, table revenues_by_territory. Années 2017 à 2021 et 2023.

Indicateurs pour l'analyse des besoins sociaux :
  - niveau de vie médian, déciles (D1, D9), rapport interdécile ; Gini et S80/S20 (2023, hors communes/EPCI)
  - taux de pauvreté au seuil de 60 % du niveau de vie médian : global, par âge du référent fiscal
    (2017-2021), par âge des individus dont enfants (2023, départements, régions, France), par statut
    d'occupation (propriétaires / locataires)
  - structure du revenu disponible : revenus d'activité, chômage, pensions, patrimoine, prestations
    sociales (familiales, logement, minima sociaux), impôts
  - part des ménages fiscaux imposés
Communes et EPCI 2023 : seuls le niveau de vie médian et le taux de pauvreté sont publiés par l'INSEE.
Communes : détail publié au-delà d'environ 1 000 ménages fiscaux (secret statistique en deçà).
"""
from app.models import RevenuesByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num

REFERENCE_AGES = {"lt30": "Moins de 30 ans", "30_39": "30-39 ans", "40_49": "40-49 ans", "50_59": "50-59 ans",
                  "60_74": "60-74 ans", "ge75": "75 ans ou plus"}
INDIVIDUAL_AGES = {"lt18": "Moins de 18 ans", "18_29": "18-29 ans", "30_39": "30-39 ans", "40_49": "40-49 ans",
                   "50_64": "50-64 ans", "65_74": "65-74 ans", "ge75": "75 ans ou plus"}
INCOME_SHARES = {"share_activity_income": "Revenus d'activité", "share_salaries": "Salaires",
                 "share_unemployment_benefits": "Indemnités de chômage", "share_self_employment": "Revenus non salariés",
                 "share_pensions": "Pensions et retraites", "share_property_income": "Revenus du patrimoine",
                 "share_social_benefits": "Prestations sociales", "share_family_benefits": "Prestations familiales",
                 "share_minimum_income": "Minima sociaux", "share_housing_benefits": "Prestations logement",
                 "share_taxes": "Impôts directs"}
FIELDS = (
    ["fiscal_households", "fiscal_persons", "median_living_standard", "taxed_households_rate", "poverty_rate",
     "poverty_rate_owners", "poverty_rate_tenants", "d1", "d2", "d3", "d4", "d6", "d7", "d8", "d9", "q1", "q3",
     "interdecile_ratio", "gini", "s80s20", "interquartile_range"]
    + [f"poverty_rate_ref_{a}" for a in REFERENCE_AGES]
    + [f"poverty_rate_ind_{a}" for a in INDIVIDUAL_AGES] + [f"median_ind_{a}" for a in INDIVIDUAL_AGES]
    + list(INCOME_SHARES)
)


class RevenuesService(TerritoryStatsService):
    MODEL = RevenuesByTerritory
    DATA_KEY = "revenues_data"
    LABEL = "revenus et pauvreté"
    EXTRA = {"labels": {"reference_ages": REFERENCE_AGES, "individual_ages": INDIVIDUAL_AGES,
                        "income_shares": INCOME_SHARES},
             "source": "INSEE, Filosofi (2017-2021 : chiffres clés ; 2023 : nouvelle diffusion)"}
    EVOLUTION_METRICS = ["median_living_standard", "poverty_rate", "poverty_rate_tenants", "poverty_rate_owners",
                         "d1", "d9", "interdecile_ratio", "taxed_households_rate"] + list(INCOME_SHARES)

    def year_data(self, row):
        d = {f: num(getattr(row, f)) for f in FIELDS}
        if d["interdecile_ratio"] is None and d["d1"] and d["d9"] is not None:
            d["interdecile_ratio"] = round(d["d9"] / d["d1"], 1)
        # Seuil de pauvreté indicatif : 60 % du niveau de vie médian national n'est pas publié ici ;
        # on expose l'écart du D1 à la médiane du territoire (profondeur relative du bas de la distribution)
        med = d["median_living_standard"]
        d["d1_to_median"] = round(d["d1"] / med * 100, 1) if d["d1"] is not None and med else None
        d["detailed"] = d["d1"] is not None or d["share_social_benefits"] is not None
        return d
