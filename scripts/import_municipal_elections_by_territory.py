"""
Import des élections municipales (1er tour) dans municipal_elections_by_territory.

Source : data/elections/municipales_<année>/municipales-<année>-resultats-communes-*.csv (ministère de l'Intérieur,
data.gouv.fr), une ligne par commune (Paris, Lyon, Marseille : commune entière), séparateur « ; ».
Inscrits, votants, exprimés, blancs, nuls ; participation = votants / inscrits (recalculée, pas les % du fichier).
EPCI, départements, régions : sommes des communes (rattachement COG 2024, département du fichier à défaut) ;
France (FM) = France métropolitaine.

Usage :
    python scripts/import_municipal_elections_by_territory.py --dry-run
    python scripts/import_municipal_elections_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

YEAR = 2026
SRC = f"data/elections/municipales_{YEAR}/municipales-{YEAR}-resultats-communes-*.csv"
COG = "data/geography/COG_au_01-01-2024.csv"
COUNTS = ["registered", "voters", "expressed", "blank", "null"]
COLUMNS = ["geo_level", "geo_code", "year"] + COUNTS + ["turnout_rate", "blank_null_rate"]
RENAME = {"Code département": "dep", "Code commune": "geo_code", "Inscrits": "registered", "Votants": "voters",
          "Exprimés": "expressed", "Blancs": "blank", "Nuls": "null"}


def read():
    path = sorted(glob.glob(SRC))[-1]
    d = pd.read_csv(path, sep=";", dtype=str, usecols=list(RENAME), encoding="utf-8-sig").rename(columns=RENAME)
    for c in COUNTS:
        d[c] = pd.to_numeric(d[c].str.replace(r"\s", "", regex=True), errors="coerce")
    d["geo_code"] = d.geo_code.str.zfill(5)
    logger.info(f"📖 {path} : {len(d):,} communes, {d.registered.sum():,.0f} inscrits, {d.voters.sum():,.0f} votants")
    return d


def aggregate(d):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo.CODGEO.str.zfill(5)
    geo["REG"] = geo.REG.str.zfill(2)
    geo["DEP"] = geo.DEP.str.zfill(2)
    d = d.merge(geo[["CODGEO", "EPCI", "REG"]], left_on="geo_code", right_on="CODGEO", how="left")
    dep_reg = geo.drop_duplicates("DEP").set_index("DEP")["REG"]
    d["REG"] = d.REG.fillna(d.dep.map(dep_reg))
    logger.info(f"   Communes absentes du COG 2024 (sans EPCI) : {d.CODGEO.isna().sum()} ; sans région : {d.REG.isna().sum()}")
    agg = lambda df, key, level: (df.groupby(key)[COUNTS].sum().reset_index()
                                  .rename(columns={key: "geo_code"}).assign(geo_level=level))
    parts = [d[["geo_code"] + COUNTS].assign(geo_level="COM"),
             agg(d[d.EPCI.notna() & (d.EPCI != "ZZZZZZZZZ")], "EPCI", "EPCI"),
             agg(d, "dep", "DEP"), agg(d[d.REG.notna()], "REG", "REG")]
    metro = d[~d.dep.str.startswith(("97", "98"))]
    parts.append(pd.DataFrame([{**metro[COUNTS].sum().to_dict(), "geo_code": "FM", "geo_level": "FRANCE"}]))
    data = pd.concat(parts, ignore_index=True)
    data["turnout_rate"] = (100 * data.voters / data.registered).where(data.registered > 0).round(2)
    data["blank_null_rate"] = (100 * (data.blank + data["null"]) / data.voters).where(data.voters > 0).round(2)
    data["year"] = YEAR
    return data.reindex(columns=COLUMNS)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(['geo_level', 'geo_code']).sum()} ; "
                f"communes sans participation : {(data.geo_level.eq('COM') & data.turnout_rate.isna()).sum()}")
    for level, code in (("COM", "59484"), ("COM", "91376"), ("COM", "75056"), ("EPCI", "200057859"), ("DEP", "59"),
                        ("REG", "32"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if not r.empty:
            r = r.iloc[0]
            logger.info(f"🔎 {level} {code} : {r.registered:,.0f} inscrits, {r.voters:,.0f} votants, "
                        f"participation {r.turnout_rate} %, blancs et nuls {r.blank_null_rate} %")


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
    for row in data[COLUMNS].itertuples(index=False):
        buf.write("\t".join("\\N" if pd.isna(v) else str(v) for v in row) + "\n")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM municipal_elections_by_territory WHERE year = %s", (YEAR,))
            cols = ", ".join(f'"{c}"' for c in COLUMNS)
            cur.copy_expert(f"COPY municipal_elections_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
            cur.execute("SELECT count(*) FROM municipal_elections_by_territory WHERE year = %s", (YEAR,))
            logger.info(f"🔎 Contrôle : {cur.fetchone()[0]:,} lignes en base pour {YEAR}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche le contrôle sans écrire")
    args = parser.parse_args()
    data = aggregate(read())
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        conn = _connect()
        try:
            write(conn, data)
            logger.info("🏁 Import terminé")
        finally:
            conn.close()
