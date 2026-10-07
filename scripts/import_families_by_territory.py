"""
Import des familles INSEE (fichier DS_RP_FAMILLE_COMP) dans families_by_territory.

Les valeurs officielles INSEE sont importées directement à chaque échelle
(aucune agrégation côté API) :
    COM, ARM (arrondissements municipaux), EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Usage :
    python scripts/import_families_by_territory.py                     # fichier par défaut
    python scripts/import_families_by_territory.py --file chemin.csv
    python scripts/import_families_by_territory.py --dry-run           # contrôle sans écrire en base

Les millésimes présents dans le fichier (ex. 2012, 2017, 2023) remplacent ceux déjà en base.
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd
import psycopg2
from sqlalchemy.engine.url import make_url

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_FILE = "data/families/territory/DS_RP_FAMILLE_COMP_2023_data.csv"
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG"]
FRANCE_CODE = "FM"  # France métropolitaine

# (TFN, NCH) INSEE -> colonne de la table
MEASURES = {
    ("_T", "_T"): "total_families",
    ("22", "_T"): "couples_with_children",
    ("21", "_T"): "couples_without_children",
    ("1", "_T"): "single_parent_families",
    ("11", "_T"): "single_fathers",
    ("12", "_T"): "single_mothers",
    ("220", "_T"): "blended_families",
    ("223", "_T"): "traditional_families",
    ("_T", "CH0_Y_LT25"): "families_0_children",
    ("_T", "CH1_Y_LT25"): "families_1_child",
    ("_T", "CH2_Y_LT25"): "families_2_children",
    ("_T", "CH3_Y_LT25"): "families_3_children",
    ("_T", "CH_GE4_Y_LT25"): "families_4_plus_children",
}
COLUMNS = ["geo_level", "geo_code", "year"] + list(MEASURES.values())


def load(path: str) -> pd.DataFrame:
    logger.info(f"📥 Lecture de {path}")
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    keep = df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))
    df = df[keep].copy()

    df["measure"] = [MEASURES.get(k) for k in zip(df["TFN"], df["NCH"])]
    df = df[df["measure"].notna()]
    # Statut K = données incluses dans une autre commune (communes fusionnées) -> NULL
    df["value"] = pd.to_numeric(df["OBS_VALUE"].where(df["OBS_STATUS"] != "K"), errors="coerce")

    wide = df.pivot(index=["GEO_OBJECT", "GEO", "TIME_PERIOD"], columns="measure", values="value").reset_index()
    wide = wide.rename(columns={"GEO_OBJECT": "geo_level", "GEO": "geo_code", "TIME_PERIOD": "year"})
    wide["year"] = wide["year"].astype(int)
    for col in MEASURES.values():
        if col not in wide.columns:
            wide[col] = float("nan")
    return wide[COLUMNS]


def check(wide: pd.DataFrame) -> None:
    logger.info("🔎 Lignes par niveau et millésime :")
    counts = wide.groupby(["geo_level", "year"]).size().unstack(fill_value=0)
    for line in counts.to_string().splitlines():
        logger.info("   " + line)

    # Contrôle de cohérence : un département officiel = somme de ses communes
    com = wide[wide.geo_level == "COM"].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    sums = com.groupby(["dep", "year"])["total_families"].sum()
    dep = wide[wide.geo_level == "DEP"].set_index(["geo_code", "year"])["total_families"]
    ecart = (dep - sums.reindex(dep.index)).abs().max()
    logger.info(f"🔎 Écart max département officiel vs somme des communes : {ecart:.6f} famille")


def write(wide: pd.DataFrame) -> None:
    url = make_url(str(engine.url))
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"

    years = sorted(wide["year"].unique().tolist())
    buf = io.StringIO()
    wide.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)

    conn = psycopg2.connect(**params)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM families_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY families_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
                buf,
            )
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        with conn.cursor() as cur:
            conn.autocommit = True
            cur.execute("ANALYZE families_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=DEFAULT_FILE)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.file)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
