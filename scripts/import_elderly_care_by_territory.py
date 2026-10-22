"""
Import de l'offre pour personnes âgées de la Base permanente des équipements (INSEE, BPE 2025) dans
elderly_care_by_territory.

Source : data/equipment/BPE25.parquet (un enregistrement par équipement) :
  - D401 « Personnes âgées : hébergement » (Ehpad, résidences autonomie, petites unités de vie…) : nombre
    d'établissements et places (CAPACITE, renseignée pour ~98 % ; établissements sans capacité comptés à part) ;
  - D402 « Personnes âgées : soins à domicile » (Ssiad) et D403 « services d'aide » (Saad) : nombre de services
    implantés (pas de capacité dans la BPE ; un service intervient au-delà de sa commune d'implantation).
Population de 75 ans ou plus : population_by_territory 2023 (pop_ge80 + 75-79 ans), lue en base. Une ligne pour chaque
territoire de la table population (communes sans équipement = 0). Arrondissements de Paris, Lyon, Marseille en ARM et
cumulés dans la commune. France (FM) = France métropolitaine, comme la population.

Usage :
    python scripts/import_elderly_care_by_territory.py --dry-run
    python scripts/import_elderly_care_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BPE = "data/equipment/BPE25.parquet"
YEAR, POPULATION_YEAR = 2025, 2023
PLM = {"751": "75056", "693": "69123", "132": "13055"}  # arrondissements → commune
MEASURES = ["housing_facilities", "housing_places", "housing_no_capacity", "home_nursing_services",
            "home_help_services", "pop_75p", "places_per_1000_75p"]
COLUMNS = ["geo_level", "geo_code", "year"] + MEASURES


def read_bpe():
    t = pq.read_table(BPE, columns=["TYPEQU", "DEPCOM", "CAPACITE", "EPCI", "DEP", "REG"],
                      filters=[("TYPEQU", "in", ["D401", "D402", "D403"])]).to_pandas()
    t["CAPACITE"] = pd.to_numeric(t["CAPACITE"], errors="coerce")
    t["housing_facilities"] = (t.TYPEQU == "D401").astype(int)
    t["housing_places"] = t["CAPACITE"].where(t.TYPEQU == "D401")
    t["housing_no_capacity"] = ((t.TYPEQU == "D401") & t["CAPACITE"].isna()).astype(int)
    t["home_nursing_services"] = (t.TYPEQU == "D402").astype(int)
    t["home_help_services"] = (t.TYPEQU == "D403").astype(int)
    logger.info(f"📖 BPE : {t.housing_facilities.sum():,} établissements d'hébergement, "
                f"{t.housing_places.sum():,.0f} places ({t.housing_no_capacity.sum()} sans capacité), "
                f"{t.home_nursing_services.sum():,} services de soins et {t.home_help_services.sum():,} services d'aide")
    return t


def aggregate(t):
    cols = ["housing_facilities", "housing_places", "housing_no_capacity", "home_nursing_services", "home_help_services"]
    agg = lambda df, key: df.groupby(key)[cols].sum(min_count=1).reset_index().rename(columns={key: "geo_code"})
    parts = []
    arm = t[t.DEPCOM.str[:3].isin(PLM)]
    parts.append(agg(arm, "DEPCOM").assign(geo_level="ARM"))
    com = t.assign(COM=t.DEPCOM.map(lambda c: PLM.get(c[:3], c)))
    parts.append(agg(com, "COM").assign(geo_level="COM"))
    parts.append(agg(t[t.EPCI.notna() & (t.EPCI != "ZZZZZZZZZ")], "EPCI").assign(geo_level="EPCI"))
    parts.append(agg(t, "DEP").assign(geo_level="DEP"))
    parts.append(agg(t, "REG").assign(geo_level="REG"))
    metro = t[~t.DEP.str.startswith("97")]
    parts.append(pd.DataFrame([{**metro[cols].sum().to_dict(), "geo_code": "FM", "geo_level": "FRANCE"}]))
    return pd.concat(parts, ignore_index=True)


def population(conn):
    sql = f"""SELECT geo_level, geo_code,
                     pop_ge80 + COALESCE(pyr_men_75_79, 0) + COALESCE(pyr_women_75_79, 0) AS pop_75p,
                     pyr_men_75_79 IS NULL AS no_pyr
              FROM population_by_territory WHERE year = {POPULATION_YEAR}"""
    pop = pd.read_sql(sql, conn)
    logger.info(f"📖 Population {POPULATION_YEAR} : {len(pop):,} territoires "
                f"({pop.no_pyr.sum()} sans tranche 75-79 ans) — " + str(pop.groupby('geo_level').size().to_dict()))
    return pop[["geo_level", "geo_code", "pop_75p"]]


def build(t, pop):
    data = aggregate(t)
    if pop is not None:
        data = pop.merge(data, on=["geo_level", "geo_code"], how="left")
        counts = ["housing_facilities", "housing_no_capacity", "home_nursing_services", "home_help_services"]
        data[counts] = data[counts].fillna(0)
        data.loc[data.housing_facilities == 0, "housing_places"] = 0
        data["places_per_1000_75p"] = (1000 * data.housing_places / data.pop_75p).where(data.pop_75p > 0).round(1)
    data["year"] = YEAR
    return data.reindex(columns=COLUMNS)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(['geo_level', 'geo_code']).sum()}")
    for level, code in (("COM", "59484"), ("COM", "75056"), ("ARM", "75115"), ("EPCI", "245901160"), ("DEP", "59"),
                        ("REG", "32"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if not r.empty:
            logger.info(f"🔎 {level} {code} : " + ", ".join(f"{m}={r.iloc[0][m]}" for m in MEASURES))


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(conn, data):
    buf = io.StringIO()
    data[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM elderly_care_by_territory")
            cols = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY elderly_care_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="sans écriture ; sans base, sans population ni taux")
    args = parser.parse_args()
    t = read_bpe()
    conn = None if args.dry_run and not os.environ.get("DATABASE_URL") else _connect()
    try:
        data = build(t, population(conn) if conn else None)
        check(data)
        if args.dry_run:
            logger.info("🧪 Dry-run : rien n'a été écrit en base")
        else:
            write(conn, data)
            logger.info("🏁 Import terminé")
    finally:
        if conn:
            conn.close()
