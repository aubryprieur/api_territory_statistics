"""
Import du pass Sport 2024 (ministère des Sports, data.gouv.fr « pass Sport - Activations journalières ») dans
pass_sport_by_territory.

Source : data/sports/pass_sport_2024_communes.csv — agrégat du fichier des activations journalières
(pass-sport-2024-activations-journalieres.csv, une ligne par pass activé, campagne du 4 juin 2024 au 3 février 2025)
par code_insee, tranche d'âge (lt6, 6_10, 11_14, 15_17, 18_24, 25p), sexe et organisme (CAF, MSA, cnous) ; colonne n.
Le code commune est celui du bénéficiaire (presque toutes les communes de France apparaissent, y compris sans club).
Arrondissements de Paris, Lyon, Marseille en ARM et cumulés dans la commune ; EPCI et région via le COG 2024 ;
France (FM) = France métropolitaine. Taux de recours : pass activés par des 6-17 ans pour 100 habitants de 6-17 ans
(recensement, education_by_territory, dernier millésime, lu en base).

Usage :
    python scripts/import_pass_sport_by_territory.py --dry-run
    python scripts/import_pass_sport_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SRC = "data/sports/pass_sport_2024_communes.csv"
COG = "data/geography/COG_au_01-01-2024.csv"
YEAR = 2024
PLM = {"751": "75056", "693": "69123", "132": "13055"}
MEASURES = ["activations", "activations_6_17", "girls_6_17", "students", "pop_6_17", "rate_6_17", "girls_share_6_17"]
COLUMNS = ["geo_level", "geo_code", "year"] + MEASURES
COUNTS = ["activations", "activations_6_17", "girls_6_17", "students"]


def read():
    d = pd.read_csv(SRC, sep=";", dtype={"code_insee": str})
    d["code_insee"] = d["code_insee"].str.zfill(5)
    kid = d["age"].isin(["6_10", "11_14", "15_17"])
    d["activations"] = d["n"]
    d["activations_6_17"] = d["n"].where(kid, 0)
    d["girls_6_17"] = d["n"].where(kid & (d["beneficiaire_sexe"] == "F"), 0)
    d["students"] = d["n"].where(d["organisme"].str.lower() == "cnous", 0)
    c = d.groupby("code_insee")[COUNTS].sum()
    logger.info(f"📖 {SRC} : {c.activations.sum():,.0f} pass activés dans {len(c):,} codes communes, "
                f"dont {c.activations_6_17.sum():,.0f} par des 6-17 ans")
    return c


def aggregate(c):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    geo["DEP"] = geo["DEP"].str.zfill(2)
    geo["REG"] = geo["REG"].str.zfill(2)
    c = c.reset_index()
    c["COM"] = c["code_insee"].map(lambda x: PLM.get(x[:3], x))
    c = c.merge(geo[["CODGEO", "EPCI", "DEP", "REG"]], left_on="COM", right_on="CODGEO", how="left")
    c["DEP"] = c["DEP"].fillna(c["COM"].map(lambda x: x[:3] if x.startswith("97") else x[:2]))
    dep_reg = geo.drop_duplicates("DEP").set_index("DEP")["REG"]
    c["REG"] = c["REG"].fillna(c["DEP"].map(dep_reg))
    valid = c["DEP"].isin(set(geo["DEP"]))
    logger.info(f"   Codes absents du COG 2024 (comptés au département) : {c.CODGEO.isna().sum()} ; "
                f"codes sans département valide (ignorés hors commune) : {(~valid).sum()} ({c.loc[~valid, 'activations'].sum():,.0f} pass)")
    c.loc[~valid, ["DEP", "REG"]] = None
    agg = lambda df, key, level: (df.groupby(key)[COUNTS].sum().reset_index()
                                  .rename(columns={key: "geo_code"}).assign(geo_level=level))
    parts = [agg(c[c.code_insee != c.COM], "code_insee", "ARM"), agg(c, "COM", "COM"),
             agg(c[c.EPCI.notna() & (c.EPCI != "ZZZZZZZZZ")], "EPCI", "EPCI"), agg(c[c.DEP.notna()], "DEP", "DEP"),
             agg(c[c.REG.notna()], "REG", "REG")]
    metro = c[c.DEP.notna() & ~c.DEP.fillna("").str.startswith("97")]
    parts.append(pd.DataFrame([{**metro[COUNTS].sum().to_dict(), "geo_code": "FM", "geo_level": "FRANCE"}]))
    return pd.concat(parts, ignore_index=True)


def population(conn):
    sql = """SELECT geo_level, geo_code, year, pop_6_10 + pop_11_14 + pop_15_17 AS pop_6_17
             FROM education_by_territory
             WHERE year = (SELECT max(year) FROM education_by_territory)"""
    pop = pd.read_sql(sql, conn)
    logger.info(f"📖 Population 6-17 ans (recensement {pop.year.max()}) : {len(pop):,} territoires")
    return pop[["geo_level", "geo_code", "pop_6_17"]]


def build(c, pop):
    data = aggregate(c)
    if pop is not None:
        data = data.merge(pop, on=["geo_level", "geo_code"], how="outer")
        data[COUNTS] = data[COUNTS].fillna(0)
        data["rate_6_17"] = (100 * data.activations_6_17 / data.pop_6_17).where(data.pop_6_17 > 0).round(1)
    data["girls_share_6_17"] = (100 * data.girls_6_17 / data.activations_6_17).where(data.activations_6_17 > 0).round(1)
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
            cur.execute("DELETE FROM pass_sport_by_territory")
            cols = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY pass_sport_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="sans écriture ; sans base, sans population ni taux")
    args = parser.parse_args()
    counts = read()
    conn = None if args.dry_run and not os.environ.get("DATABASE_URL") else _connect()
    try:
        data = build(counts, population(conn) if conn else None)
        check(data)
        if args.dry_run:
            logger.info("🧪 Dry-run : rien n'a été écrit en base")
        else:
            write(conn, data)
            logger.info("🏁 Import terminé")
    finally:
        if conn:
            conn.close()
