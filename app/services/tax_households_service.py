"""
Foyers fiscaux — DGFiP, impôt sur le revenu par collectivité territoriale (IRCOM), revenus 2021 et 2024, table
tax_households_by_territory (scripts/import_tax_households_by_territory.py).

Indicateurs : part des foyers fiscaux imposés, revenu fiscal de référence (RFR) moyen par foyer (euros courants),
impôt net moyen, part des foyers percevant des salaires, des retraites ou pensions, répartition des foyers par
tranche de RFR (communes d'environ 2 000 foyers ou plus, départements, régions, France ; EPCI si toutes leurs
communes sont détaillées). Le foyer fiscal n'est pas le ménage : un couple non marié forme deux foyers.
"""
from app.models import TaxHouseholdsByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

BRACKETS = {"hh_0_10k": "0 à 10 000 €", "hh_10_12k": "10 001 à 12 000 €", "hh_12_15k": "12 001 à 15 000 €",
            "hh_15_20k": "15 001 à 20 000 €", "hh_20_30k": "20 001 à 30 000 €", "hh_30_50k": "30 001 à 50 000 €",
            "hh_50_100k": "50 001 à 100 000 €", "hh_100k_plus": "Plus de 100 000 €"}
FIELDS = ["households", "rfr", "net_tax", "taxed_households", "wage_households", "pension_households"] + list(BRACKETS)
SOURCE = "DGFiP, impôt sur le revenu par collectivité territoriale (IRCOM), revenus 2021 et 2024"


def per_household(amount_k, households):
    if amount_k is None or not households:
        return None
    return round(amount_k * 1000 / households)


class TaxHouseholdsService(TerritoryStatsService):
    MODEL = TaxHouseholdsByTerritory
    DATA_KEY = "tax_households_data"
    LABEL = "foyers fiscaux"
    EXTRA = {"brackets": BRACKETS, "source": SOURCE}
    EVOLUTION_METRICS = ["taxed_share", "rfr_avg", "pension_share", "low_rfr_share"]

    def year_data(self, row):
        d = {f: num(getattr(row, f)) for f in FIELDS}
        n = d["households"]
        d["taxed_share"] = pct(d["taxed_households"], n)
        d["wage_share"] = pct(d["wage_households"], n)
        d["pension_share"] = pct(d["pension_households"], n)
        d["rfr_avg"] = per_household(d["rfr"], n)
        d["net_tax_avg"] = per_household(d["net_tax"], n)
        d["low_rfr_share"] = pct(d["hh_0_10k"], n)
        lt15 = [d["hh_0_10k"], d["hh_10_12k"], d["hh_12_15k"]]
        d["lt15k_share"] = pct(total(*lt15), n) if all(v is not None for v in lt15) else None
        hi = [d["hh_50_100k"], d["hh_100k_plus"]]
        d["ge50k_share"] = pct(total(*hi), n) if all(v is not None for v in hi) else None
        return d
