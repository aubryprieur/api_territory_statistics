"""
Import des ménages INSEE dans households_by_territory, à toutes les échelles
(valeurs officielles INSEE, aucune agrégation côté API) :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources (recensement de la population, millésimes 2012, 2017, 2023) :
  - DS_RP_MENAGES_COMP (CSV)      : ménages et population des ménages par type de ménage
                                    et par PCS de la personne de référence
  - DS_RP_MENAGES_PRINC (parquet) : personnes vivant seules et population des ménages par âge

Usage :
    python scripts/import_households_by_territory.py              # fichiers par défaut
    python scripts/import_households_by_territory.py --dry-run    # contrôles sans écrire en base
    python scripts/import_households_by_territory.py --comp f.csv --princ f.parquet

Lecture du parquet : nécessite pyarrow (pip install pyarrow) si absent.
Les millésimes présents dans les fichiers remplacent ceux déjà en base.
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

DEFAULT_COMP = "data/households/territory/DS_RP_MENAGES_COMP_2023_data.csv"
DEFAULT_PRINC = "data/households/territory/DS_RP_MENAGES_PRINC_2023.parquet"
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG"]
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]

# DS_RP_MENAGES_COMP : (RP_MEASURE, TPH, PCS) -> colonne
COMP_MEASURES = {
    ("DWELLINGS", "_T", "_T"): "households",
    ("DWELLINGS_POPSIZE", "_T", "_T"): "household_population",
    ("DWELLINGS", "11", "_T"): "one_person",
    ("DWELLINGS", "110", "_T"): "men_alone",
    ("DWELLINGS", "111", "_T"): "women_alone",
    ("DWELLINGS", "12", "_T"): "other_without_family",
    ("DWELLINGS", "2", "_T"): "with_family",
    ("DWELLINGS", "MF21", "_T"): "single_parent",
    ("DWELLINGS", "MF221", "_T"): "couple_without_children",
    ("DWELLINGS", "MF222", "_T"): "couple_with_children",
    **{("DWELLINGS", "_T", c): f"pcs_{c}" for c in ["1", "2", "3", "4", "5", "6", "7", "9"]},
}

# DS_RP_MENAGES_PRINC : (RP_MEASURE, AGE) -> colonne
AGES = {"Y15T24": "15_24", "Y25T39": "25_39", "Y40T54": "40_54",
        "Y55T64": "55_64", "Y65T79": "65_79", "Y_GE80": "80_plus"}
PRINC_MEASURES = {
    **{("ONEPERS", a): f"living_alone_{s}" for a, s in AGES.items()},
    **{("DWELLINGS_POPSIZE", a): f"household_population_{s}" for a, s in AGES.items()},
}

COLUMNS = KEY + list(COMP_MEASURES.values()) + list(PRINC_MEASURES.values())


def _keep_geo(df):
    return df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))


def load_comp(path):
    logger.info(f"📥 Lecture de {path} (par blocs)")
    parts = []
    usecols = ["GEO", "GEO_OBJECT", "RP_MEASURE", "TPH", "PCS", "OBS_STATUS", "TIME_PERIOD", "OBS_VALUE"]
    for chunk in pd.read_csv(path, sep=";", dtype=str, usecols=usecols, keep_default_na=False, chunksize=500_000):
        chunk = chunk[_keep_geo(chunk)]
        chunk = chunk.assign(measure=[COMP_MEASURES.get(k) for k in zip(chunk.RP_MEASURE, chunk.TPH, chunk.PCS)])
        chunk = chunk[chunk["measure"].notna()]
        # Statut K = données incluses dans une autre commune (communes fusionnées) -> NULL
        chunk = chunk.assign(
            value=pd.to_numeric(chunk["OBS_VALUE"].where(chunk["OBS_STATUS"] != "K"), errors="coerce"),
            year=chunk["TIME_PERIOD"].astype(int),
        )
        parts.append(chunk[["GEO_OBJECT", "GEO", "year", "measure", "value"]])
    df = pd.concat(parts, ignore_index=True)
    return df.rename(columns={"GEO_OBJECT": "geo_level", "GEO": "geo_code"}) \
             .pivot(index=KEY, columns="measure", values="value")


def load_princ(path):
    logger.info(f"📥 Lecture de {path}")
    df = pd.read_parquet(path, columns=["GEO", "GEO_OBJECT", "TIME_PERIOD", "RP_MEASURE", "AGE",
                                         "COUPLE", "CIVIL_STATUS", "OBS_VALUE", "OBS_STATUS"])
    df = df[_keep_geo(df) & df["COUPLE"].eq("_T") & df["CIVIL_STATUS"].eq("_T")]
    df = df.assign(measure=[PRINC_MEASURES.get(k) for k in zip(df.RP_MEASURE, df.AGE)])
    df = df[df["measure"].notna()]
    df = df.assign(
        value=pd.to_numeric(df["OBS_VALUE"].where(df["OBS_STATUS"] != "K"), errors="coerce"),
        year=pd.to_datetime(df["TIME_PERIOD"]).dt.year.astype(int),
    )
    return df.rename(columns={"GEO_OBJECT": "geo_level", "GEO": "geo_code"}) \
             .pivot(index=KEY, columns="measure", values="value")


def load(comp_path, princ_path):
    wide = load_comp(comp_path).join(load_princ(princ_path), how="outer").reset_index()
    for col in COLUMNS:
        if col not in wide.columns:
            wide[col] = float("nan")
    return wide[COLUMNS]


def check(wide):
    logger.info("🔎 Lignes par niveau et millésime :")
    for line in wide.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    com = wide[wide.geo_level == "COM"].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    dep = wide[wide.geo_level == "DEP"].set_index(["geo_code", "year"])
    for col in ["households", "living_alone_80_plus"]:
        sums = com.groupby(["dep", "year"])[col].sum()
        ecart = (dep[col] - sums.reindex(dep.index)).abs().max()
        logger.info(f"🔎 {col} : écart max département officiel vs somme des communes = {ecart:.6f}")
    fm = wide[(wide.geo_level == "FRANCE")].set_index("year")
    logger.info("🔎 France métropolitaine, ménages : " +
                ", ".join(f"{y} = {v:,.0f}" for y, v in fm["households"].items()))


def write(wide):
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    years = sorted(int(y) for y in wide["year"].unique())
    buf = io.StringIO()
    wide.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = psycopg2.connect(**params)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM households_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY households_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE households_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comp", default=DEFAULT_COMP)
    parser.add_argument("--princ", default=DEFAULT_PRINC)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.comp, args.princ)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
