"""
Logement — INSEE, recensement (DS_RP_LOGEMENT_PRINC / _COMP), table housing_by_territory.
Millésimes 2012, 2017, 2023 ; valeurs officielles par territoire.

Indicateurs pour l'analyse des besoins sociaux :
  - parc : résidences principales, secondaires, logements vacants ; maisons / appartements
  - statut d'occupation : propriétaires, locataires du parc privé, du parc social (HLM), meublés, logés gratuitement
  - taille et peuplement : nombre de pièces, personnes par logement, suroccupation / sous-occupation
  - mobilité résidentielle : ancienneté d'emménagement (part des emménagés récents, ancienneté moyenne)
  - conditions de vie : ménages sans voiture, stationnement, combustible de chauffage (fioul), âge du parc
"""
from app.models import HousingByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

TENURES = {"owners": "Propriétaires", "tenants_private": "Locataires du parc privé",
           "tenants_social": "Locataires HLM", "tenants_furnished": "Locataires d'un meublé ou d'une chambre d'hôtel",
           "free": "Logés gratuitement"}
ROOMS = {"r1": "1 pièce", "r2": "2 pièces", "r3": "3 pièces", "r4": "4 pièces", "r5p": "5 pièces ou plus"}
STAYS = {"lt2": "Moins de 2 ans", "2_4": "2 à 4 ans", "5_9": "5 à 9 ans", "10_19": "10 à 19 ans",
         "20_29": "20 à 29 ans", "ge30": "30 ans ou plus"}
HEATING = {"town_gas": "Gaz de ville, réseau de chaleur", "electric": "Électricité", "oil": "Fioul",
           "bottled_gas": "Gaz en bouteille ou citerne", "other": "Autre (bois, pompe à chaleur...)"}
OCCUPANCY = {"over_severe": "Suroccupation accentuée", "over_moderate": "Suroccupation modérée",
             "standard": "Peuplement normal", "under_moderate": "Sous-occupation modérée",
             "under_severe": "Sous-occupation accentuée", "under_very_severe": "Sous-occupation très accentuée"}
BUILT = {"before_1946": "Avant 1946", "1946_1990": "1946 à 1990", "after_1990": "Après 1990"}
BUILT_DETAIL = {"lt1919": "Avant 1919", "1919_1945": "1919 à 1945", "1946_1970": "1946 à 1970",
                "1971_1990": "1971 à 1990", "1991_2005": "1991 à 2005", "2006_plus": "2006 ou après"}

COUNT_FIELDS = (
    ["dwellings", "dwellings_main", "dwellings_secondary", "dwellings_vacant", "dwellings_houses",
     "dwellings_apartments", "main_houses", "main_apartments", "main_rooms", "main_tenants"]
    + [f"main_{k}" for k in ROOMS] + [f"main_{k}" for k in TENURES]
    + ["pop_main", "pop_owners", "pop_tenants", "pop_tenants_social"]
    + [f"stay_{k}" for k in STAYS] + ["stay_years", "stay_years_owners", "stay_years_tenants", "stay_years_social"]
    + [f"heat_{k}" for k in HEATING] + ["with_parking", "cars_0", "cars_1", "cars_2p"]
    + [f"occ_{k}" for k in OCCUPANCY] + ["occ_total"]
    + [f"built_{k}" for k in BUILT] + [f"built_{k}" for k in BUILT_DETAIL] + ["built_known"]
)


def _ratio(a, b, digits=2):
    return round(a / b, digits) if a is not None and b else None


class HousingService(TerritoryStatsService):
    MODEL = HousingByTerritory
    DATA_KEY = "housing_data"
    LABEL = "logement"
    EXTRA = {"labels": {"tenures": TENURES, "rooms": ROOMS, "stays": STAYS, "heating": HEATING,
                        "occupancy": OCCUPANCY, "built": BUILT, "built_detail": BUILT_DETAIL}}
    EVOLUTION_METRICS = (
        ["dwellings", "dwellings_main", "vacancy_rate", "secondary_rate", "houses_percentage", "main_houses_percentage"]
        + [f"{k}_percentage" for k in TENURES] + ["tenants_percentage"]
        + [f"rooms_{k}_percentage" for k in ROOMS] + ["small_dwellings_percentage", "average_rooms",
                                                      "persons_per_dwelling"]
        + ["overcrowding_rate", "severe_overcrowding_rate", "under_occupation_rate"]
        + [f"stay_{k}_percentage" for k in STAYS] + ["recent_movers_percentage", "long_stay_percentage",
                                                      "average_stay", "average_stay_owners", "average_stay_tenants",
                                                      "average_stay_social"]
        + ["no_car_percentage", "two_cars_percentage", "parking_percentage"]
        + [f"heat_{k}_percentage" for k in HEATING]
    )

    def year_data(self, row):
        c = {f: num(getattr(row, f)) for f in COUNT_FIELDS}
        d = dict(c)
        dw, main = c["dwellings"], c["dwellings_main"]

        # --- Parc de logements (% de l'ensemble des logements)
        d["main_rate"] = pct(main, dw)
        d["secondary_rate"] = pct(c["dwellings_secondary"], dw)
        d["vacancy_rate"] = pct(c["dwellings_vacant"], dw)
        d["houses_percentage"] = pct(c["dwellings_houses"], dw)
        d["apartments_percentage"] = pct(c["dwellings_apartments"], dw)
        d["main_houses_percentage"] = pct(c["main_houses"], main)        # % des résidences principales
        d["main_apartments_percentage"] = pct(c["main_apartments"], main)

        # --- Statut d'occupation (% des résidences principales)
        for k in TENURES:
            d[f"{k}_percentage"] = pct(c[f"main_{k}"], main)
        d["tenants_percentage"] = pct(c["main_tenants"], main)

        # --- Taille et peuplement
        for k in ROOMS:
            d[f"rooms_{k}_percentage"] = pct(c[f"main_{k}"], main)
        d["small_dwellings_percentage"] = pct(total(c["main_r1"], c["main_r2"]), main)  # 1-2 pièces
        d["average_rooms"] = _ratio(c["main_rooms"], main, 1)
        d["persons_per_dwelling"] = _ratio(c["pop_main"], main)
        d["persons_per_dwelling_social"] = _ratio(c["pop_tenants_social"], c["main_tenants_social"])
        occ = c["occ_total"]
        for k in OCCUPANCY:
            d[f"occ_{k}_percentage"] = pct(c[f"occ_{k}"], occ)
        d["overcrowding_rate"] = pct(total(c["occ_over_severe"], c["occ_over_moderate"]), occ)
        d["severe_overcrowding_rate"] = pct(c["occ_over_severe"], occ)
        d["under_occupation_rate"] = pct(
            total(c["occ_under_moderate"], c["occ_under_severe"], c["occ_under_very_severe"]), occ)

        # --- Ancienneté d'emménagement (% des ménages)
        for k in STAYS:
            d[f"stay_{k}_percentage"] = pct(c[f"stay_{k}"], main)
        d["recent_movers_percentage"] = d["stay_lt2_percentage"]
        d["long_stay_percentage"] = pct(total(c["stay_10_19"], c["stay_20_29"], c["stay_ge30"]), main)  # 10 ans ou +
        d["average_stay"] = _ratio(c["stay_years"], main, 1)
        d["average_stay_owners"] = _ratio(c["stay_years_owners"], c["main_owners"], 1)
        d["average_stay_tenants"] = _ratio(c["stay_years_tenants"], c["main_tenants"], 1)
        d["average_stay_social"] = _ratio(c["stay_years_social"], c["main_tenants_social"], 1)

        # --- Voitures, stationnement, chauffage (% des ménages / résidences principales)
        d["no_car_percentage"] = pct(c["cars_0"], main)
        d["one_car_percentage"] = pct(c["cars_1"], main)
        d["two_cars_percentage"] = pct(c["cars_2p"], main)
        d["parking_percentage"] = pct(c["with_parking"], main)
        heat_total = total(*(c[f"heat_{k}"] for k in HEATING))
        for k in HEATING:
            d[f"heat_{k}_percentage"] = pct(c[f"heat_{k}"], heat_total)

        # --- Période de construction (% des résidences principales construites avant le recensement - 2 ans)
        for k in BUILT:
            d[f"built_{k}_percentage"] = pct(c[f"built_{k}"], c["built_known"])
        for k in BUILT_DETAIL:
            d[f"built_{k}_percentage"] = pct(c[f"built_{k}"], c["built_known"])
        return d
