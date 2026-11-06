"""
Localisation des équipements de la Base permanente des équipements (BPE 2025, INSEE) pour les cartes du tableau de
bord : types de app/services/equipment_points_service.py (ALL_TYPES), coordonnées converties en WGS84 (EPSG 4326)
depuis la projection de chaque territoire (Lambert 93 en métropole, UTM outre-mer). Table equipment_points.

Source (data/equipment/) : bpe25_slim.parquet (ou BPE25.parquet), colonnes DEPCOM, EPCI, LIBCOM, NOMRS, TYPEQU, QP2024,
LAMBERT_X, LAMBERT_Y, EPSG, QUALITE_XY. Les équipements sans coordonnées sont ignorés.

Usage (DATABASE_URL de Heroku exporté) :
    python scripts/import_equipment_points.py --dry-run
    python scripts/import_equipment_points.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd
from pyproj import Transformer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.equipment_points_service import ALL_TYPES, YEAR  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/equipment"
COLUMNS = ["DEPCOM", "EPCI", "LIBCOM", "NOMRS", "TYPEQU", "QP2024", "LAMBERT_X", "LAMBERT_Y", "EPSG", "QUALITE_XY"]


def read():
    for name in ("bpe25_slim.parquet", "BPE25.parquet"):
        path = os.path.join(DIR, name)
        if os.path.exists(path):
            df = pd.read_parquet(path, columns=COLUMNS)
            logger.info(f"📖 {path} : {len(df):,} équipements")
            return df
    raise FileNotFoundError(f"BPE introuvable dans {DIR}")


def build(df):
    df = df[df.TYPEQU.isin(ALL_TYPES)].dropna(subset=["LAMBERT_X", "LAMBERT_Y", "EPSG"]).copy()
    df["lat"], df["lon"] = float("nan"), float("nan")
    for epsg, idx in df.groupby("EPSG").groups.items():
        tr = Transformer.from_crs(f"EPSG:{int(float(epsg))}", "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(df.loc[idx, "LAMBERT_X"].astype(float).values, df.loc[idx, "LAMBERT_Y"].astype(float).values)
        df.loc[idx, "lon"], df.loc[idx, "lat"] = lon, lat
        logger.info(f"   EPSG {epsg} : {len(idx):,} équipements")
    df = df.dropna(subset=["lat", "lon"])
    qp = df.QP2024.fillna("")
    out = pd.DataFrame({
        "year": YEAR, "typequ": df.TYPEQU, "depcom": df.DEPCOM.astype(str).str.zfill(5),
        "epci": df.EPCI.where(df.EPCI.notna() & ~df.EPCI.isin(["ZZZZZZZZZ", ""]), None),
        "commune_name": df.LIBCOM.str.title(), "name": df.NOMRS,
        "lat": df.lat.round(6), "lon": df.lon.round(6),
        "qpv": qp.str.startswith("QN") | qp.str.startswith("QP"),  # code de quartier prioritaire (QP2024)
        "quality": df.QUALITE_XY,
    })
    logger.info(f"🔢 {len(out):,} équipements géolocalisés ; par type : {out.typequ.value_counts().to_dict()}")
    v = out[out.depcom == "59606"]
    logger.info(f"🔎 Valenciennes (59606) : {len(v)} équipements, ex. {v[['typequ', 'name', 'lat', 'lon']].head(3).to_dict('records')}")
    return out


def _connect():
    import psycopg2
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(out):
    conn = _connect()
    cols = ["year", "typequ", "depcom", "epci", "commune_name", "name", "lat", "lon", "qpv", "quality"]
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM equipment_points WHERE year = %s", (YEAR,))
            buf = io.StringIO()
            o = out[cols].copy()
            for c in ("commune_name", "name"):
                o[c] = (o[c].astype("string").str.replace("\t", " ", regex=False).str.replace("\n", " ", regex=False)
                        .str.replace("\\", "/", regex=False))
            o.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
            buf.seek(0)
            cur.copy_expert(f"COPY equipment_points ({', '.join(cols)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ equipment_points : {cur.rowcount:,} lignes")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche le contrôle sans écrire")
    args = parser.parse_args()
    out = build(read())
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(out)
        logger.info("🏁 Import terminé")
