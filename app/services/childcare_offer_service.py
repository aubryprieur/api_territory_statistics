"""
Accueil du jeune enfant — Cnaf (data.caf.fr), table childcare_by_territory. Années 2017 à 2023.

Pour chaque territoire (communes publiées par la Cnaf, EPCI, départements, régions, France entière hors
Mayotte) : nombre de places et taux de couverture (places pour 100 enfants de moins de 3 ans) par mode :
  - accueil collectif (EAJE) : financé par la prestation de service unique (PSU) ou hors PSU (micro-crèches Paje...)
  - préscolarisation (enfants de 2 ans scolarisés)
  - accueil individuel : assistantes maternelles, garde à domicile
Les communes non détaillées par la Cnaf n'ont que le taux global 2020 et 2021 (fichiers TAUXCOUV).
"""
from app.models import ChildcareByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct

FRANCE_CODE = "FE"  # France entière hors Mayotte
MODES = {"eaje_psu": "Accueil collectif financé par la PSU (crèches...)",
         "eaje_hors_psu": "Accueil collectif hors PSU (micro-crèches Paje...)",
         "eaje": "Accueil collectif (EAJE)",
         "preschool": "Préscolarisation (enfants de 2 ans)",
         "childminder": "Assistantes maternelles",
         "home_care": "Garde à domicile",
         "individual": "Accueil individuel"}
COUNT_FIELDS = [f"places_{m}" for m in MODES] + ["places_total"]
RATE_FIELDS = [f"rate_{m}" for m in MODES] + ["rate_global"]


class ChildcareOfferService(TerritoryStatsService):
    MODEL = ChildcareByTerritory
    DATA_KEY = "childcare_data"
    LABEL = "accueil du jeune enfant"
    EXTRA = {"labels": {"modes": MODES}, "source": "Cnaf, data.caf.fr — accueil du jeune enfant",
             "france_scope": "France entière hors Mayotte"}
    EVOLUTION_METRICS = RATE_FIELDS + COUNT_FIELDS + ["children_under3_estimate"]

    def year_data(self, row):
        d = {f: num(getattr(row, f)) for f in COUNT_FIELDS + RATE_FIELDS}
        d["detailed"] = row.source == "cnaf_detail"
        total, rate = d["places_total"], d["rate_global"]
        # Enfants de moins de 3 ans (dénominateur Cnaf) déduits des places et du taux global
        d["children_under3_estimate"] = round(total / rate * 100) if total is not None and rate else None
        for m in ("eaje", "eaje_psu", "eaje_hors_psu", "preschool", "childminder", "home_care", "individual"):
            d[f"places_{m}_share"] = pct(d[f"places_{m}"], total)   # répartition de l'offre (% des places)
        return d

    def france(self, start_year=None, end_year=None):
        """France entière hors Mayotte (périmètre de publication de la Cnaf)."""
        return self.get("FRANCE", FRANCE_CODE, start_year, end_year)
