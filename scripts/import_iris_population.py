"""
scripts/import_iris_population.py
----------------------------------
Importe un millésime du fichier de population IRIS dans la table iris_population.
Supporte l'ajout de nouveaux millésimes sans écraser les existants (upsert).

Usage :
    # Import millésime 2022
    python scripts/import_iris_population.py \\
        --file data/iris/base-ic-evol-struct-pop-2022.CSV \\
        --year 2022

    # Remplacement complet d'un millésime déjà chargé
    python scripts/import_iris_population.py \\
        --file data/iris/base-ic-evol-struct-pop-2023.CSV \\
        --year 2023 \\
        --replace
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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

# ── Mapping colonnes CSV → colonnes BDD ───────────────────────────────────────
# Les fichiers INSEE utilisent P{YY}_* (ex. P22_POP pour 2022, P23_POP pour 2023)
# Le mapping est construit dynamiquement à partir de l'année passée en argument.

STATIC_MAP = {
    "IRIS": "iris_code",
    "COM":  "com_code",
}

def build_column_map(year: int) -> dict:
    """Construit le mapping colonnes CSV → BDD pour un millésime donné."""
    yy = str(year)[-2:]   # "22" pour 2022, "23" pour 2023, etc.
    prefix = f"P{yy}_"
    return {
        **STATIC_MAP,
        f"{prefix}POP":     "pop",
        f"{prefix}POP0002":  "pop_0_2",
        f"{prefix}POP0305": "pop_3_5",
        f"{prefix}POP0610": "pop_6_10",
        f"{prefix}POP1117": "pop_11_17",
        f"{prefix}POP1824": "pop_18_24",
        f"{prefix}POP2539": "pop_25_39",
        f"{prefix}POP4054": "pop_40_54",
        f"{prefix}POP5564": "pop_55_64",
        f"{prefix}POP6579": "pop_65_79",
        f"{prefix}POP80P":  "pop_80_plus",
        f"{prefix}POP_ETR": "pop_foreign",
        f"{prefix}POP_IMM": "pop_immigrant",
        f"{prefix}POPF":    "pop_women",
        f"{prefix}POPH":    "pop_men",
    }


def normalize_code(value, length: int):
    if pd.isna(value):
        return None
    return str(value).strip().zfill(length)


def load_csv(path: str) -> pd.DataFrame:
    logger.info(f"📂 Lecture du fichier : {path}")
    for sep, enc in [(";", "latin-1"), (";", "utf-8"), (",", "utf-8")]:
        try:
            df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, low_memory=False)
            logger.info(f"   → {len(df):,} lignes chargées (sep='{sep}', enc='{enc}')")
            return df
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"Impossible de lire le fichier : {path}")


def prepare_dataframe(df: pd.DataFrame, year: int) -> pd.DataFrame:
    column_map = build_column_map(year)

    missing = [c for c in column_map if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans le CSV pour le millésime {year} : {missing}\n"
            f"Colonnes disponibles : {list(df.columns)}"
        )

    df = df[list(column_map.keys())].copy()
    df.rename(columns=column_map, inplace=True)

    df["iris_code"] = df["iris_code"].apply(lambda v: normalize_code(v, 9))
    df["com_code"]  = df["com_code"].apply(lambda v: normalize_code(v, 5))
    df["year"]      = year

    numeric_cols = [c for c in df.columns if c not in ("iris_code", "com_code", "year")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].str.replace(",", "."), errors="coerce")

    df = df.dropna(subset=["iris_code", "com_code"])
    logger.info(f"   → {len(df):,} lignes après nettoyage")
    return df


def delete_millesime(cur, year: int):
    """Supprime uniquement le millésime ciblé (les autres sont préservés)."""
    logger.info(f"🗑️  Suppression du millésime {year} existant...")
    cur.execute("DELETE FROM iris_population WHERE year = %s;", (year,))
    logger.info(f"   → lignes supprimées : {cur.rowcount:,}")


def optimize_for_import(cur):
    cur.execute("SET work_mem = '512MB';")
    cur.execute("SET maintenance_work_mem = '512MB';")
    cur.execute("SET synchronous_commit = off;")
    logger.info("⚙️  Paramètres d'import optimisés")


def bulk_insert(conn, cur, df: pd.DataFrame):
    logger.info(f"⬆️  Insertion de {len(df):,} lignes via COPY...")
    columns = list(df.columns)
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, sep="\t", na_rep="\\N")
    buffer.seek(0)
    cur.copy_from(buffer, "iris_population", sep="\t", null="\\N", columns=columns)
    conn.commit()
    logger.info("✅ Insertion terminée")


def check_existing_millesime(cur, year: int) -> int:
    cur.execute("SELECT COUNT(*) FROM iris_population WHERE year = %s;", (year,))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Import IRIS population — multi-millésime")
    parser.add_argument("--file",    required=True,  help="Chemin vers le CSV INSEE")
    parser.add_argument("--year",    required=True,  type=int, help="Millésime à importer (ex. 2022)")
    parser.add_argument("--replace", action="store_true",
                        help="Remplace le millésime s'il existe déjà (défaut : erreur si existant)")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        logger.error(f"❌ Fichier introuvable : {args.file}")
        sys.exit(1)

    df = load_csv(args.file)
    df = prepare_dataframe(df, args.year)

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        optimize_for_import(cur)

        # Vérifie si le millésime existe déjà
        existing = check_existing_millesime(cur, args.year)
        if existing > 0:
            if args.replace:
                delete_millesime(cur, args.year)
                conn.commit()
            else:
                logger.error(
                    f"❌ Le millésime {args.year} contient déjà {existing:,} lignes.\n"
                    f"   Utilise --replace pour l'écraser."
                )
                sys.exit(1)

        bulk_insert(conn, cur, df)

        # Vérification
        cur.execute("SELECT COUNT(*) FROM iris_population WHERE year = %s;", (args.year,))
        count = cur.fetchone()[0]

        cur.execute("SELECT DISTINCT year FROM iris_population ORDER BY year;")
        all_years = [r[0] for r in cur.fetchall()]

        conn.commit()
        logger.info(f"🎉 Millésime {args.year} importé — {count:,} IRIS")
        logger.info(f"   Millésimes disponibles en base : {all_years}")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erreur : {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
