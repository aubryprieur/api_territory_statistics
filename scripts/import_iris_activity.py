"""
scripts/import_iris_activity.py
---------------------------------
Importe le fichier INSEE « base-ic-activite-residents-{year}.xlsx »
dans la table iris_activity.

Usage :
    python scripts/import_iris_activity.py \
        --file data/iris/base-ic-activite-residents-2022.xlsx \
        --year 2022

    python scripts/import_iris_activity.py \
        --file data/iris/base-ic-activite-residents-2023.xlsx \
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
        "IRIS":    "iris_code",
        "COM":     "com_code",
        "LIBIRIS": "iris_name",
        "DEP":     "dep_code",
        "REG":     "reg_code",
        # Population
        f"{p}POP1564": "pop_15_64",
        f"{p}POP1524": "pop_15_24",
        f"{p}POP2554": "pop_25_54",
        f"{p}POP5564": "pop_55_64",
        f"{p}H1564":   "pop_men_15_64",
        f"{p}H1524":   "pop_men_15_24",
        f"{p}H2554":   "pop_men_25_54",
        f"{p}H5564":   "pop_men_55_64",
        f"{p}F1564":   "pop_women_15_64",
        f"{p}F1524":   "pop_women_15_24",
        f"{p}F2554":   "pop_women_25_54",
        f"{p}F5564":   "pop_women_55_64",
        # Actifs
        f"{p}ACT1564":  "active_15_64",
        f"{p}ACT1524":  "active_15_24",
        f"{p}ACT2554":  "active_25_54",
        f"{p}ACT5564":  "active_55_64",
        f"{p}HACT1564": "active_men_15_64",
        f"{p}HACT1524": "active_men_15_24",
        f"{p}HACT2554": "active_men_25_54",
        f"{p}HACT5564": "active_men_55_64",
        f"{p}FACT1564": "active_women_15_64",
        f"{p}FACT1524": "active_women_15_24",
        f"{p}FACT2554": "active_women_25_54",
        f"{p}FACT5564": "active_women_55_64",
        # Actifs occupés
        f"{p}ACTOCC1564":  "employed_15_64",
        f"{p}ACTOCC1524":  "employed_15_24",
        f"{p}ACTOCC2554":  "employed_25_54",
        f"{p}ACTOCC5564":  "employed_55_64",
        f"{p}HACTOCC1564": "employed_men_15_64",
        f"{p}HACTOCC1524": "employed_men_15_24",
        f"{p}HACTOCC2554": "employed_men_25_54",
        f"{p}HACTOCC5564": "employed_men_55_64",
        f"{p}FACTOCC1564": "employed_women_15_64",
        f"{p}FACTOCC1524": "employed_women_15_24",
        f"{p}FACTOCC2554": "employed_women_25_54",
        f"{p}FACTOCC5564": "employed_women_55_64",
        # Chômeurs
        f"{p}CHOM1564": "unemp_15_64",
        f"{p}CHOM1524": "unemp_15_24",
        f"{p}CHOM2554": "unemp_25_54",
        f"{p}CHOM5564": "unemp_55_64",
        # Actifs par diplôme
        f"{p}ACT_DIPLMIN": "active_no_dip",
        f"{p}ACT_BEPC":    "active_bepc",
        f"{p}ACT_CAPBEP":  "active_capbep",
        f"{p}ACT_BAC":     "active_bac",
        f"{p}ACT_SUP2":    "active_sup2",
        f"{p}ACT_SUP34":   "active_sup34",
        f"{p}ACT_SUP5":    "active_sup5",
        # Chômeurs par diplôme
        f"{p}CHOM_DIPLMIN": "unemp_no_dip",
        f"{p}CHOM_BEPC":    "unemp_bepc",
        f"{p}CHOM_CAPBEP":  "unemp_capbep",
        f"{p}CHOM_BAC":     "unemp_bac",
        f"{p}CHOM_SUP2":    "unemp_sup2",
        f"{p}CHOM_SUP34":   "unemp_sup34",
        f"{p}CHOM_SUP5":    "unemp_sup5",
        # Inactifs
        f"{p}INACT1564":   "inactive_15_64",
        f"{p}HINACT1564":  "inactive_men_15_64",
        f"{p}FINACT1564":  "inactive_women_15_64",
        f"{p}ETUD1564":    "student_15_64",
        f"{p}HETUD1564":   "student_men_15_64",
        f"{p}FETUD1564":   "student_women_15_64",
        f"{p}RETR1564":    "retired_15_64",
        f"{p}HRETR1564":   "retired_men_15_64",
        f"{p}FRETR1564":   "retired_women_15_64",
        f"{p}AINACT1564":  "other_inactive_15_64",
        f"{p}HAINACT1564": "other_inactive_men_15_64",
        f"{p}FAINACT1564": "other_inactive_women_15_64",
        # CSP actifs (compl)
        f"{c}ACT1564_STAT_GSEC11_21": "act_farmers",
        f"{c}ACT1564_STAT_GSEC12_22": "act_craftsmen",
        f"{c}ACT1564_STAT_GSEC13_23": "act_executives",
        f"{c}ACT1564_STAT_GSEC14_24": "act_intermediary",
        f"{c}ACT1564_STAT_GSEC15_25": "act_employees",
        f"{c}ACT1564_STAT_GSEC16_26": "act_workers",
        f"{c}ACTOCC1564_STAT_GSEC11": "emp_farmers",
        f"{c}ACTOCC1564_STAT_GSEC12": "emp_craftsmen",
        f"{c}ACTOCC1564_STAT_GSEC13": "emp_executives",
        f"{c}ACTOCC1564_STAT_GSEC14": "emp_intermediary",
        f"{c}ACTOCC1564_STAT_GSEC15": "emp_employees",
        f"{c}ACTOCC1564_STAT_GSEC16": "emp_workers",
        # Actifs occupés 15+
        f"{p}ACTOCC15P":  "employed_15p",
        f"{p}HACTOCC15P": "employed_men_15p",
        f"{p}FACTOCC15P": "employed_women_15p",
        # Salariés / non-salariés
        f"{p}SAL15P":   "salaried_15p",
        f"{p}HSAL15P":  "salaried_men_15p",
        f"{p}FSAL15P":  "salaried_women_15p",
        f"{p}NSAL15P":  "self_emp_15p",
        f"{p}HNSAL15P": "self_emp_men_15p",
        f"{p}FNSAL15P": "self_emp_women_15p",
        # Temps partiel
        f"{p}ACTOCC15P_TP": "employed_15p_pt",
        f"{p}SAL15P_TP":    "salaried_15p_pt",
        f"{p}HSAL15P_TP":   "salaried_men_pt",
        f"{p}FSAL15P_TP":   "salaried_women_pt",
        f"{p}NSAL15P_TP":   "self_emp_15p_pt",
        # Type de contrat
        f"{p}SAL15P_CDI":    "sal_cdi",
        f"{p}SAL15P_CDD":    "sal_cdd",
        f"{p}SAL15P_INTERIM":"sal_interim",
        f"{p}SAL15P_EMPAID": "sal_aided",
        f"{p}SAL15P_APPR":   "sal_appr",
        # Non-salariés par type
        f"{p}NSAL15P_INDEP":  "self_emp_indep",
        f"{p}NSAL15P_EMPLOY": "self_emp_employ",
        f"{p}NSAL15P_AIDFAM": "self_emp_family",
        # Lieu de travail
        f"{p}ACTOCC15P_ILT1":  "work_same_commune",
        f"{p}ACTOCC15P_ILT2P": "work_other_commune",
        f"{p}ACTOCC15P_ILT3":  "work_other_dep_same_reg",
        f"{p}ACTOCC15P_ILT4":  "work_other_reg_metro",
        f"{p}ACTOCC15P_ILT5":  "work_other_reg_domtom",
        # Transport (compl)
        f"{c}ACTOCC15P_PAS":      "transport_none",
        f"{c}ACTOCC15P_MAR":      "transport_walk",
        f"{c}ACTOCC15P_VELO":     "transport_bike",
        f"{c}ACTOCC15P_2ROUESMOT":"transport_moto",
        f"{c}ACTOCC15P_VOIT":     "transport_car",
        f"{c}ACTOCC15P_TCOM":     "transport_transit",
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
    cur.execute("DELETE FROM iris_activity WHERE year = %s;", (year,))
    logger.info(f"   → {cur.rowcount:,} lignes supprimées")


def bulk_insert(conn, cur, df: pd.DataFrame):
    logger.info(f"⬆️  Insertion de {len(df):,} lignes via COPY...")
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)
    cur.copy_from(buffer, "iris_activity", sep="\t", null="\\N", columns=list(df.columns))
    conn.commit()
    logger.info("✅ Insertion terminée")


def check_existing(cur, year: int) -> int:
    cur.execute("SELECT COUNT(*) FROM iris_activity WHERE year = %s;", (year,))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Import IRIS activité résidents — multi-millésime")
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

        cur.execute("SELECT COUNT(*) FROM iris_activity WHERE year = %s;", (args.year,))
        count = cur.fetchone()[0]
        cur.execute("SELECT DISTINCT year FROM iris_activity ORDER BY year;")
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
