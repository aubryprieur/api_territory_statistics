"""
Import des contours IRIS simplifiés dans iris_geometries.

Source : data/geography/iris/iris_geometries_2024.csv.gz, produit par scripts/build_iris_geometries.py à partir de
l'export OpenDataSoft « georef-france-iris » (découpage 2024). Ce script ne dépend que de pandas et psycopg2.

Usage :
    python scripts/import_iris_geometries.py --dry-run
    python scripts/import_iris_geometries.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE = "data/geography/iris/iris_geometries_2024.csv.gz"
COLUMNS = ["iris_code", "com_code", "com_parent", "iris_name", "iris_type", "label_lon", "label_lat", "geometry"]


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.source, dtype=str)
    logger.info(f"📖 {len(df):,} IRIS, {df['com_parent'].nunique():,} communes, "
                f"géométries {df['geometry'].str.len().sum() / 1e6:,.1f} Mo")
    logger.info(f"   Doublons : {df['iris_code'].duplicated().sum()} ; types : {df['iris_type'].value_counts().to_dict()}")
    q = df[df["com_parent"] == "59484"]
    logger.info(f"   Quiévrechain : {list(zip(q['iris_code'], q['iris_name']))}")
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
        return
    # Écriture au format texte de COPY sans guillemets CSV : les contours GeoJSON contiennent des « " » que
    # to_csv entourerait de guillemets (JSON illisible ensuite). Échappement des seuls caractères spéciaux de COPY.
    def cell(v):
        if v is None or (isinstance(v, float) and v != v):
            return "\\N"
        return str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ").replace("\r", " ")

    buf = io.StringIO()
    for row in df[COLUMNS].itertuples(index=False):
        buf.write("\t".join(cell(v) for v in row) + "\n")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM iris_geometries")
            cols = ", ".join(COLUMNS)
            cur.copy_expert(f"COPY iris_geometries ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} IRIS importés")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE iris_geometries")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logger.info("🏁 Import terminé")


if __name__ == "__main__":
    main()
