"""
Tissu économique local — INSEE, Flores (établissements actifs et postes salariés au 31 décembre 2017 et 2021),
table economic_fabric_by_territory.

Taux calculés :
  - répartition des établissements et des postes salariés par grand secteur
  - part des postes dans la sphère présentielle (activités tournées vers les besoins des habitants) et dans le
    domaine public
  - part des petits établissements (moins de 10 salariés) et des postes dans les établissements de 50 salariés ou +
  - particuliers employeurs d'assistants maternels pour 100 enfants de moins de 5 ans (recensement 2023 ; ordre
    de grandeur, les familles peuvent employer une assistante maternelle pour des enfants plus âgés)
Évolution 2017 → 2021.
"""
from app.database import SessionLocal
from app.models import EconomicFabricByTerritory, PopulationByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct, total

SECTORS = {
    "agriculture": "Agriculture",
    "industry": "Industrie",
    "construction": "Construction",
    "market_services": "Commerce, transports, services marchands",
    "trade": "dont commerce",
    "non_market": "Administration publique, enseignement, santé, action sociale",
}
FIELDS = [c for c in EconomicFabricByTerritory.__table__.columns.keys() if c not in ("geo_level", "geo_code", "year")]
DENOMINATOR_YEAR = 2023


class EconomicFabricService(TerritoryStatsService):
    MODEL = EconomicFabricByTerritory
    DATA_KEY = "economic_fabric_data"
    LABEL = "tissu économique local"
    EXTRA = {"labels": {"sectors": SECTORS},
             "source": "INSEE, Flores — établissements actifs et postes salariés au 31 décembre"}
    EVOLUTION_METRICS = (["ets_total", "posts_total", "childminder_employers", "presential_posts_share",
                          "public_posts_share", "small_ets_share", "large_ets_posts_share"]
                         + [f"posts_{s}_share" for s in SECTORS])

    def children_under_5(self, level, code):
        db = SessionLocal()
        try:
            row = (db.query(PopulationByTerritory)
                   .filter(PopulationByTerritory.geo_level == level, PopulationByTerritory.geo_code == str(code),
                           PopulationByTerritory.year == DENOMINATOR_YEAR).first())
            return total(num(row.pyr_men_0_4), num(row.pyr_women_0_4)) if row else None
        except Exception:
            return None
        finally:
            db.close()

    def year_data(self, row):
        d = {f: num(getattr(row, f)) for f in FIELDS}
        posts, ets = d["posts_total"], d["ets_total"]
        for s in SECTORS:
            d[f"posts_{s}_share"] = pct(d[f"posts_{s}"], posts)
            d[f"ets_{s}_share"] = pct(d[f"ets_{s}"], ets)
        other_market = (d["posts_market_services"] - d["posts_trade"]
                        if d["posts_market_services"] is not None and d["posts_trade"] is not None else None)
        d["posts_other_market_share"] = pct(other_market, posts)  # transports et services marchands hors commerce
        d["presential_posts_share"] = pct(d["posts_presential"], posts)
        d["public_posts_share"] = pct(total(d["posts_presential_public"], d["posts_productive_public"]), posts)
        d["small_ets_share"] = pct(total(d["ets_size_0"], d["ets_size_1_9"]), ets)
        d["large_ets_posts_share"] = pct(total(d["posts_size_50_99"], d["posts_size_100p"]), posts)
        d["posts_per_ets"] = round(posts / ets, 1) if posts is not None and ets else None
        for size in ("0", "1_9", "10_19", "20_49", "50p"):
            d[f"ets_size_{size}_share"] = pct(d[f"ets_size_{size}"], ets)
        return d

    def get(self, level, code, start_year=None, end_year=None):
        result = super().get(level, code, start_year, end_year)
        if "error" in result:
            return result
        children = self.children_under_5(level, code)
        for d in result[self.DATA_KEY].values():
            d["children_under_5"] = children
            d["childminder_employers_per_100_children"] = pct(d["childminder_employers"], children)
        result["evolution"] = self.evolution(result[self.DATA_KEY], start_year, end_year)
        return result
