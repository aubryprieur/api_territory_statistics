"""
scripts/import_iris_education.py
----------------------------------
Importe le fichier INSEE « base-ic-diplomes-formation-{year}.xlsx »
dans la table iris_education.

Usage :
    python scripts/import_iris_education.py \
        --file data/iris/base-ic-diplomes-formation-2022.xlsx \
        --year 2022

    python scripts/import_iris_education.py \
        --file data/iris/base-ic-diplomes-formation-2023.xlsx \
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
    return {
        "IRIS":                    "iris_code",
        "COM":                     "com_code",
        "LIBIRIS":                 "iris_name",
        "DEP":                     "dep_code",
        "REG":                     "reg_code",
        f"{p}POP0205":             "pop_2_5",
        f"{p}POP0610":             "pop_6_10",
        f"{p}POP1114":             "pop_11_14",
        f"{p}POP1517":             "pop_15_17",
        f"{p}POP1824":             "pop_18_24",
        f"{p}POP2529":             "pop_25_29",
        f"{p}POP30P":              "pop_30p",
        f"{p}SCOL0205":            "scol_2_5",
        f"{p}SCOL0610":            "scol_6_10",
        f"{p}SCOL1114":            "scol_11_14",
        f"{p}SCOL1517":            "scol_15_17",
        f"{p}SCOL1824":            "scol_18_24",
        f"{p}SCOL2529":            "scol_25_29",
        f"{p}SCOL30P":             "scol_30p",
        f"{p}NSCOL15P":            "nscol_15p",
        f"{p}NSCOL15P_DIPLMIN":    "nscol_15p_no_dip",
        f"{p}NSCOL15P_BEPC":       "nscol_15p_bepc",
        f"{p}NSCOL15P_CAPBEP":     "nscol_15p_capbep",
        f"{p}NSCOL15P_BAC":        "nscol_15p_bac",
        f"{p}NSCOL15P_SUP2":       "nscol_15p_sup2",
        f"{p}NSCOL15P_SUP34":      "nscol_15p_sup34",
        f"{p}NSCOL15P_SUP5":       "nscol_15p_sup5",
        f"{p}HNSCOL15P":           "nscol_15p_men",
        f"{p}HNSCOL15P_DIPLMIN":   "nscol_15p_men_no_dip",
        f"{p}HNSCOL15P_BEPC":      "nscol_15p_men_bepc",
        f"{p}HNSCOL15P_CAPBEP":    "nscol_15p_men_capbep",
        f"{p}HNSCOL15P_BAC":       "nscol_15p_men_bac",
        f"{p}HNSCOL15P_SUP2":      "nscol_15p_men_sup2",
        f"{p}HNSCOL15P_SUP34":     "nscol_15p_men_sup34",
        f"{p}HNSCOL15P_SUP5":      "nscol_15p_men_sup5",
        f"{p}FNSCOL15P":           "nscol_15p_women",
        f"{p}FNSCOL15P_DIPLMIN":   "nscol_15p_women_no_dip",
        f"{p}FNSCOL15P_BEPC":      "nscol_15p_women_bepc",
        f"{p}FNSCOL15P_CAPBEP":    "nscol_15p_women_capbep",
        f"{p}FNSCOL15P_BAC":       "nscol_15p_women_bac",
        f"{p}FNSCOL15P_SUP2":      "nscol_15p_women_sup2",
        f"{p}FNSCOL15P_SUP34":     "nscol_15p_women_sup34",
        f"{p}FNSCOL15P_SUP5":      "nscol_15p_women_sup5",
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
    cur.execute("DELETE FROM iris_education WHERE year = %s;", (year,))
    logger.info(f"   → {cur.rowcount:,} lignes supprimées")


def bulk_insert(conn, cur, df: pd.DataFrame):
    logger.info(f"⬆️  Insertion de {len(df):,} lignes via COPY...")
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)
    cur.copy_from(buffer, "iris_education", sep="\t", null="\\N", columns=list(df.columns))
    conn.commit()
    logger.info("✅ Insertion terminée")


def check_existing(cur, year: int) -> int:
    cur.execute("SELECT COUNT(*) FROM iris_education WHERE year = %s;", (year,))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Import IRIS diplômes/formation — multi-millésime")
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

        cur.execute("SELECT COUNT(*) FROM iris_education WHERE year = %s;", (args.year,))
        count = cur.fetchone()[0]
        cur.execute("SELECT DISTINCT year FROM iris_education ORDER BY year;")
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
