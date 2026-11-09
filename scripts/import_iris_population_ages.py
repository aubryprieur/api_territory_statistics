"""
Tranches d'âge à l'IRIS du nouveau format Insee (recensement 2023, fichier DS_RP_POPULATION_PRINC_IRIS_2023.parquet) :
moins de 20 ans, 65 ans ou plus, moins de 2 ans, 2-5 ans, 11-14 ans, 15-17 ans. Complète les lignes 2023 de
iris_population (déjà importées depuis base-ic-evol-struct-pop-2023) ; les IRIS absents de la table sont signalés.

Usage (DATABASE_URL de Heroku exporté) :
    python scripts/import_iris_population_ages.py --dry-run
    python scripts/import_iris_population_ages.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd
import pyarrow.parquet as pq

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FILE = "data/iris/2023/DS_RP_POPULATION_PRINC_IRIS_2023.parquet"
YEAR = 2023
AGES = {"Y_LT20": "pop_lt20", "Y_GE65": "pop_ge65", "Y_LT2": "pop_lt2", "Y2T5": "pop_2_5",
        "Y11T14": "pop_11_14", "Y15T17": "pop_15_17"}


def read():
    t = pq.read_table(FILE, columns=["GEO", "GEO_OBJECT", "AGE", "SEX", "IMMI", "NATIONALITY_TYPE", "HAR", "OBS_VALUE"],
                      filters=[("GEO_OBJECT", "=", "IRIS"), ("SEX", "=", "_T"), ("AGE", "in", list(AGES))]).to_pandas()
    t = t[(t.IMMI == "_T") & (t.NATIONALITY_TYPE == "_T") & (t.HAR == "_T")]
    wide = t.pivot_table(index="GEO", columns="AGE", values="OBS_VALUE", aggfunc="first").rename(columns=AGES)
    wide = wide.reindex(columns=list(AGES.values())).reset_index().rename(columns={"GEO": "iris_code"})
    logger.info(f"📖 {FILE} : {len(wide):,} IRIS")
    r = wide[wide.iris_code == "010040101"]
    logger.info(f"🔎 010040101 : {r.iloc[0].to_dict() if not r.empty else 'absent'}")
    return wide


def _connect():
    import psycopg2
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(wide):
    cols = list(AGES.values())
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE TEMP TABLE tmp_ages (iris_code varchar(9), {', '.join(c + ' float' for c in cols)}) ON COMMIT DROP")
            buf = io.StringIO()
            wide[["iris_code"] + cols].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
            buf.seek(0)
            cur.copy_expert(f"COPY tmp_ages (iris_code, {', '.join(cols)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            cur.execute(f"UPDATE iris_population p SET {', '.join(f'{c} = t.{c}' for c in cols)} "
                        f"FROM tmp_ages t WHERE p.iris_code = t.iris_code AND p.year = %s", (YEAR,))
            logger.info(f"✅ iris_population {YEAR} : {cur.rowcount:,} IRIS complétés")
            cur.execute("SELECT count(*) FROM tmp_ages t WHERE NOT EXISTS (SELECT 1 FROM iris_population p "
                        "WHERE p.iris_code = t.iris_code AND p.year = %s)", (YEAR,))
            logger.info(f"🔎 IRIS du fichier absents de iris_population {YEAR} : {cur.fetchone()[0]:,}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="lit le fichier et affiche le contrôle sans écrire")
    args = parser.parse_args()
    wide = read()
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(wide)
        logger.info("🏁 Import terminé")
