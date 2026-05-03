"""
scripts/import_iris_families.py
---------------------------------
Importe le fichier INSEE « base-ic-couples-familles-menages-{year}.xlsx »
dans la table iris_families.

Usage :
    python scripts/import_iris_families.py \
        --file data/iris/base-ic-couples-familles-menages-2022.xlsx \
        --year 2022

    # Remplacement d'un millésime existant
    python scripts/import_iris_families.py \
        --file data/iris/base-ic-couples-familles-menages-2023.xlsx \
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

# ── Connexion ──────────────────────────────────────────────────────────────────
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
        "IRIS":              "iris_code",
        "COM":               "com_code",
        "LIBIRIS":           "iris_name",
        "DEP":               "dep_code",
        "REG":               "reg_code",
        f"{p}POP15P":        "pop_15p",
        f"{p}POP1524":       "pop_15_24",
        f"{p}POP2554":       "pop_25_54",
        f"{p}POP5579":       "pop_55_79",
        f"{p}POP80P":        "pop_80p",
        f"{p}POP15P_PSEUL":  "pop_15p_alone",
        f"{p}POP1524_PSEUL": "pop_15_24_alone",
        f"{p}POP2554_PSEUL": "pop_25_54_alone",
        f"{p}POP5579_PSEUL": "pop_55_79_alone",
        f"{p}POP80P_PSEUL":  "pop_80p_alone",
        f"{c}FAM":           "families",
        f"{c}COUPAENF":      "couples_with_children",
        f"{c}FAMMONO":       "single_parent",
        f"{c}COUPSENF":      "couples_no_children",
        f"{c}NE24F0":        "families_0_children",
        f"{c}NE24F1":        "families_1_child",
        f"{c}NE24F2":        "families_2_children",
        f"{c}NE24F3":        "families_3_children",
        f"{c}NE24F4P":       "families_4p_children",
    }


def normalize_iris(value) -> str:
    return None if pd.isna(value) else str(value).strip().zfill(9)

def normalize_com(value) -> str:
    return None if pd.isna(value) else str(value).strip().zfill(5)

def normalize_dep(value) -> str:
    if pd.isna(value):
        return None
    v = str(value).strip()
    return v if v.upper() in ("2A", "2B") or len(v) == 3 else v.zfill(2)

def normalize_reg(value) -> str:
    if pd.isna(value):
        return None
    s = str(value).strip()
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
    cur.execute("DELETE FROM iris_families WHERE year = %s;", (year,))
    logger.info(f"   → {cur.rowcount:,} lignes supprimées")


def bulk_insert(conn, cur, df: pd.DataFrame):
    logger.info(f"⬆️  Insertion de {len(df):,} lignes via COPY...")
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)
    cur.copy_from(buffer, "iris_families", sep="\t", null="\\N", columns=list(df.columns))
    conn.commit()
    logger.info("✅ Insertion terminée")


def check_existing(cur, year: int) -> int:
    cur.execute("SELECT COUNT(*) FROM iris_families WHERE year = %s;", (year,))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Import IRIS familles — multi-millésime")
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
                logger.error(
                    f"❌ Le millésime {args.year} contient déjà {existing:,} lignes. "
                    f"Utilise --replace pour l'écraser."
                )
                sys.exit(1)

        bulk_insert(conn, cur, df)

        cur.execute("SELECT COUNT(*) FROM iris_families WHERE year = %s;", (args.year,))
        count = cur.fetchone()[0]
        cur.execute("SELECT DISTINCT year FROM iris_families ORDER BY year;")
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
