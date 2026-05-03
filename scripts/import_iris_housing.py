"""
scripts/import_iris_housing.py
--------------------------------
Importe le fichier INSEE « base-ic-logement-{year}.xlsx »
dans la table iris_housing.

Usage :
    python scripts/import_iris_housing.py \
        --file data/iris/base-ic-logement-2022.xlsx \
        --year 2022

    python scripts/import_iris_housing.py \
        --file data/iris/base-ic-logement-2023.xlsx \
        --year 2023 --replace
"""

import sys
import os
import argparse
import logging
import psycopg2
import pandas as pd
from io import StringIO
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

parsed = urlparse(DATABASE_URL)
DB_CONFIG = {
    "host":     parsed.hostname,
    "port":     parsed.port,
    "database": parsed.path[1:],
    "user":     parsed.username,
    "password": parsed.password,
    "sslmode":  "require",
}


def build_column_map(year: int) -> dict:
    yy = str(year)[-2:]
    p  = f"P{yy}_"
    c  = f"C{yy}_"
    return {
        "IRIS":                   "iris_code",
        "COM":                    "com_code",
        "LIBIRIS":                "iris_name",
        "DEP":                    "dep_code",
        "REG":                    "reg_code",
        f"{p}LOG":                "housing_total",
        f"{p}RP":                 "main_res",
        f"{p}RSECOCC":            "second_res",
        f"{p}LOGVAC":             "vacant",
        f"{p}MAISON":             "houses",
        f"{p}APPART":             "apartments",
        f"{p}RP_1P":              "rp_1room",
        f"{p}RP_2P":              "rp_2rooms",
        f"{p}RP_3P":              "rp_3rooms",
        f"{p}RP_4P":              "rp_4rooms",
        f"{p}RP_5PP":             "rp_5p_rooms",
        f"{p}RP_M30M2":           "rp_u30m2",
        f"{p}RP_3040M2":          "rp_30_40m2",
        f"{p}RP_4060M2":          "rp_40_60m2",
        f"{p}RP_6080M2":          "rp_60_80m2",
        f"{p}RP_80100M2":         "rp_80_100m2",
        f"{p}RP_100120M2":        "rp_100_120m2",
        f"{p}RP_120M2P":          "rp_120p_m2",
        f"{p}RP_ACH1919":         "rp_built_pre1919",
        f"{p}RP_ACH1945":         "rp_built_1919_1945",
        f"{p}RP_ACH1970":         "rp_built_1946_1970",
        f"{p}RP_ACH1990":         "rp_built_1971_1990",
        f"{p}RP_ACH2005":         "rp_built_1991_2005",
        f"{p}RP_ACH2019":         "rp_built_2006_2019",
        f"{p}MEN":                "households",
        f"{p}MEN_ANEM0002":       "hh_moved_u2y",
        f"{p}MEN_ANEM0204":       "hh_moved_2_4y",
        f"{p}MEN_ANEM0509":       "hh_moved_5_9y",
        f"{p}MEN_ANEM10P":        "hh_moved_10py",
        f"{p}RP_PROP":            "rp_owners",
        f"{p}RP_LOC":             "rp_renters",
        f"{p}RP_LOCHLMV":         "rp_social_housing",
        f"{p}RP_GRAT":            "rp_free",
        f"{p}RP_CGAZV":           "heat_gas_network",
        f"{p}RP_CFIOUL":          "heat_fuel",
        f"{p}RP_CELEC":           "heat_electric",
        f"{p}RP_CGAZB":           "heat_gas_bottle",
        f"{p}RP_CAUT":            "heat_other",
        f"{p}RP_VOIT1P":          "hh_1p_car",
        f"{p}RP_VOIT1":           "hh_1_car",
        f"{p}RP_VOIT2P":          "hh_2p_cars",
        f"{c}RP_NORME":           "rp_standard_occ",
        f"{c}RP_SOUSOCC_MOD":     "rp_mild_underuse",
        f"{c}RP_SOUSOCC_ACC":     "rp_heavy_underuse",
        f"{c}RP_SOUSOCC_TACC":    "rp_extreme_underuse",
        f"{c}RP_SUROCC_MOD":      "rp_mild_overuse",
        f"{c}RP_SUROCC_ACC":      "rp_heavy_overuse",
    }


def normalize_iris(v): return None if pd.isna(v) else str(v).strip().zfill(9)
def normalize_com(v):  return None if pd.isna(v) else str(v).strip().zfill(5)
def normalize_dep(v):
    if pd.isna(v): return None
    s = str(v).strip()
    return s if s.upper() in ("2A", "2B") or len(s) == 3 else s.zfill(2)
def normalize_reg(v):
    if pd.isna(v): return None
    s = str(v).strip()
    return str(int(float(s))) if s.replace('.', '').isdigit() else s


def load_file(path: str) -> pd.DataFrame:
    logger.info(f"📂 Lecture du fichier : {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str, engine="openpyxl")
    else:
        for sep, enc in [(";", "latin-1"), (";", "utf-8"), (",", "utf-8")]:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
    logger.info(f"   → {len(df):,} lignes, {len(df.columns)} colonnes")
    return df


def prepare_dataframe(df: pd.DataFrame, year: int) -> pd.DataFrame:
    column_map = build_column_map(year)
    missing = [c for c in column_map if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes pour le millésime {year} : {missing}\n"
            f"Colonnes disponibles : {list(df.columns)}"
        )
    df = df[list(column_map.keys())].copy()
    df.rename(columns=column_map, inplace=True)

    df["iris_code"] = df["iris_code"].apply(normalize_iris)
    df["com_code"]  = df["com_code"].apply(normalize_com)
    df["dep_code"]  = df["dep_code"].apply(normalize_dep)
    df["reg_code"]  = df["reg_code"].apply(normalize_reg)
    df["iris_name"] = df["iris_name"].apply(lambda v: str(v).strip() if pd.notna(v) else None)
    df["year"]      = year

    numeric_cols = [c for c in df.columns if c not in
                    ("iris_code", "com_code", "iris_name", "dep_code", "reg_code", "year")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")

    df = df.dropna(subset=["iris_code", "com_code"])
    logger.info(f"   → {len(df):,} lignes après nettoyage")
    return df


def optimize_for_import(cur):
    cur.execute("SET work_mem = '512MB';")
    cur.execute("SET maintenance_work_mem = '512MB';")
    cur.execute("SET synchronous_commit = off;")
    logger.info("⚙️  Paramètres d'import optimisés")


def delete_millesime(cur, year: int):
    logger.info(f"🗑️  Suppression du millésime {year}...")
    cur.execute("DELETE FROM iris_housing WHERE year = %s;", (year,))
    logger.info(f"   → {cur.rowcount:,} lignes supprimées")


def bulk_insert(conn, cur, df: pd.DataFrame):
    logger.info(f"⬆️  Insertion de {len(df):,} lignes via COPY...")
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)
    cur.copy_from(buffer, "iris_housing", sep="\t", null="\\N", columns=list(df.columns))
    conn.commit()
    logger.info("✅ Insertion terminée")


def check_existing(cur, year: int) -> int:
    cur.execute("SELECT COUNT(*) FROM iris_housing WHERE year = %s;", (year,))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Import IRIS logement — multi-millésime")
    parser.add_argument("--file",    required=True, help="Chemin vers le fichier Excel ou CSV")
    parser.add_argument("--year",    required=True, type=int, help="Millésime (ex. 2022)")
    parser.add_argument("--replace", action="store_true", help="Remplace le millésime si existant")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        logger.error(f"❌ Fichier introuvable : {args.file}")
        sys.exit(1)

    df = load_file(args.file)
    df = prepare_dataframe(df, args.year)

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        optimize_for_import(cur)
        existing = check_existing(cur, args.year)
        if existing > 0:
            if args.replace:
                delete_millesime(cur, args.year)
                conn.commit()
            else:
                logger.error(f"❌ Millésime {args.year} déjà présent ({existing:,} lignes). Utilise --replace.")
                sys.exit(1)

        bulk_insert(conn, cur, df)

        cur.execute("SELECT COUNT(*) FROM iris_housing WHERE year = %s;", (args.year,))
        count = cur.fetchone()[0]
        cur.execute("SELECT DISTINCT year FROM iris_housing ORDER BY year;")
        all_years = [r[0] for r in cur.fetchall()]
        conn.commit()

        logger.info(f"🎉 Millésime {args.year} importé — {count:,} IRIS")
        logger.info(f"   Millésimes disponibles : {all_years}")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erreur : {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
