"""
Import emploi / activité / chômage / emplois / navettes INSEE dans employment_by_territory,
à toutes les échelles (valeurs officielles INSEE, aucune agrégation côté API) :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources (recensement de la population, millésimes 2012, 2017, 2023) :
  - DS_RP_EMPLOI_LR_PRINC (parquet) : population 15-64 ans par activité, âge, sexe (et diplôme en 2023)
  - DS_RP_EMPLOI_LR_COMP  (parquet) : actifs / actifs occupés 15-64 ans par catégorie socioprofessionnelle
  - DS_RP_EMPLOI_LT_PRINC (parquet) : emplois au lieu de travail (statut, temps partiel, sexe)
  - DS_RP_EMPLOI_LT_COMP  (parquet) : emplois au lieu de travail par secteur d'activité
  - DS_RP_NAVETTES_PRINC  (csv ou parquet) : actifs occupés par lieu de travail et mode de transport

Usage :
    python scripts/import_employment_by_territory.py              # fichiers par défaut
    python scripts/import_employment_by_territory.py --dry-run    # contrôles sans écrire en base

Nécessite pyarrow (pip install pyarrow). Les millésimes présents remplacent ceux déjà en base.
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

DIR = "data/employment/territory"
DEFAULTS = {
    "lr_princ": f"{DIR}/DS_RP_EMPLOI_LR_PRINC_2023.parquet",
    "lr_comp": f"{DIR}/DS_RP_EMPLOI_LR_COMP_2023.parquet",
    "lt_princ": f"{DIR}/DS_RP_EMPLOI_LT_PRINC_2023.parquet",
    "lt_comp": f"{DIR}/DS_RP_EMPLOI_LT_COMP_2023.parquet",
    "navettes": f"{DIR}/DS_RP_NAVETTES_PRINC_2023_data.csv",
}
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG"]
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]

AGES = {"Y15T64": "15_64", "Y15T24": "15_24", "Y25T54": "25_54", "Y55T64": "55_64"}
SEXES = {"_T": "", "M": "_men", "F": "_women"}
STATUS = {"_T": "pop", "1T2": "active", "1": "employed", "2": "unemployed"}
INACTIVE = {"31": "retired", "33": "students", "35": "homemakers", "36": "other_inactive"}
DIPLOMAS = {"001T100_RP": "no_diploma", "200_RP": "bepc", "300_RP": "cap_bep", "350T351_RP": "bac",
            "500_RP": "bac2", "600_RP": "bac3_4", "700_RP": "bac5_plus"}

# --- DS_RP_EMPLOI_LR_PRINC : (EMPSTA_ENQ, AGE, SEX, EDUC) -> colonne
LR_PRINC = {}
for st, p in STATUS.items():
    for ag, a in AGES.items():
        for sx, s in SEXES.items():
            LR_PRINC[(st, ag, sx, "_T")] = f"{p}_{a}{s}"
for st, p in INACTIVE.items():
    for sx, s in SEXES.items():
        LR_PRINC[(st, "Y15T64", sx, "_T")] = f"{p}_15_64{s}"
LR_PRINC[("1", "Y_GE15", "_T", "_T")] = "employed_15_plus"
for ed, d in DIPLOMAS.items():
    LR_PRINC[("1T2", "Y15T64", "_T", ed)] = f"active_{d}"
    LR_PRINC[("2", "Y15T64", "_T", ed)] = f"unemployed_{d}"

# --- DS_RP_EMPLOI_LR_COMP : (EMPSTA_ENQ, AGE, PCS) -> colonne
LR_COMP = {}
for c in "123456":
    LR_COMP[("1T2", "Y15T64", c)] = f"active_pcs_{c}"
    LR_COMP[("1", "Y15T64", c)] = f"employed_pcs_{c}"

# --- DS_RP_EMPLOI_LT_PRINC : (EMPFORM, SEX, WKTIME, AGE) -> colonne  (EMPFORM 1 = non salariés, 2 = salariés)
LT_PRINC = {
    ("_T", "_T", "_T", "_T"): "jobs",
    ("2", "_T", "_T", "_T"): "jobs_salaried",
    ("1", "_T", "_T", "_T"): "jobs_non_salaried",
    ("2", "_T", "PT", "_T"): "jobs_salaried_part_time",
    ("_T", "F", "_T", "_T"): "jobs_women",
}

# --- DS_RP_EMPLOI_LT_COMP : (EMP_ACTIVITY, SEX, PCS, EMPFORM) -> colonne
LT_COMP = {
    ("AZ", "_T", "_T", "_T"): "jobs_agriculture",
    ("BE", "_T", "_T", "_T"): "jobs_industry",
    ("FZ", "_T", "_T", "_T"): "jobs_construction",
    ("GU", "_T", "_T", "_T"): "jobs_trade_services",
    ("OQ", "_T", "_T", "_T"): "jobs_public_services",
}

# --- DS_RP_NAVETTES_PRINC : (TRANS, WORK_AREA, AGE, EMPSTA_ENQ) -> colonne
NAVETTES = {
    ("_T", "_T", "Y_GE15", "1"): "workers",
    ("_T", "10", "Y_GE15", "1"): "work_in_commune",
    ("_T", "21", "Y_GE15", "1"): "work_other_commune_dep",
    ("_T", "22", "Y_GE15", "1"): "work_other_dep_region",
    ("_T", "23", "Y_GE15", "1"): "work_other_region",
    ("_T", "24T30", "Y_GE15", "1"): "work_abroad_overseas",
    ("1", "_T", "Y_GE15", "1"): "commute_none",
    ("2", "_T", "Y_GE15", "1"): "commute_walk",
    ("3", "_T", "Y_GE15", "1"): "commute_bike",          # 2017 et 2023
    ("3T4", "_T", "Y_GE15", "1"): "commute_two_wheels",  # publié tel quel en 2012 ; recalculé (3 + 4) ensuite
    ("4", "_T", "Y_GE15", "1"): "_commute_motorbike",    # intermédiaire
    ("5", "_T", "Y_GE15", "1"): "commute_car",
    ("6", "_T", "Y_GE15", "1"): "commute_public",
}

SOURCES = [
    ("lr_princ", ["EMPSTA_ENQ", "AGE", "SEX", "EDUC"], LR_PRINC),
    ("lr_comp", ["EMPSTA_ENQ", "AGE", "PCS"], LR_COMP),
    ("lt_princ", ["EMPFORM", "SEX", "WKTIME", "AGE"], LT_PRINC),
    ("lt_comp", ["EMP_ACTIVITY", "SEX", "PCS", "EMPFORM"], LT_COMP),
    ("navettes", ["TRANS", "WORK_AREA", "AGE", "EMPSTA_ENQ"], NAVETTES),
]
COLUMNS = KEY + [c for _, _, m in SOURCES for c in m.values() if not c.startswith("_")]


def _filter(df, dims, mapping):
    keep = df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))
    df = df[keep]
    # Correspondance vectorisée : clé "dim1|dim2|..." -> colonne
    joined = {"|".join(k): v for k, v in mapping.items()}
    key = df[dims[0]].astype(str)
    for d in dims[1:]:
        key = key + "|" + df[d].astype(str)
    measure = key.map(joined)
    df = df[measure.notna()]
    measure = measure[measure.notna()]
    # Statut K = données incluses dans une autre commune (communes fusionnées) -> NULL
    value = pd.to_numeric(df["OBS_VALUE"].where(df["OBS_STATUS"].astype(str) != "K"), errors="coerce")
    year = df["TIME_PERIOD"].astype(str).str[:4].astype(int)
    return pd.DataFrame({"geo_level": df["GEO_OBJECT"].astype(str).values, "geo_code": df["GEO"].astype(str).values,
                         "year": year.values, "measure": measure.values, "value": value.values})


def _read(path, dims, mapping):
    logger.info(f"📥 Lecture de {path}")
    cols = ["GEO", "GEO_OBJECT", "TIME_PERIOD", *dims, "OBS_VALUE", "OBS_STATUS"]
    if path.endswith(".csv"):
        parts = [_filter(chunk, dims, mapping) for chunk in
                 pd.read_csv(path, sep=";", dtype=str, usecols=cols, keep_default_na=False, chunksize=500_000)]
    else:
        # Lecture année par année, filtrée sur les niveaux utiles : limite la mémoire nécessaire
        import pyarrow.parquet as pq
        years = pq.read_table(path, columns=["TIME_PERIOD"]).column(0).unique().to_pylist()
        parts = []
        for y in sorted(years):
            table = pq.read_table(path, columns=cols, filters=[("GEO_OBJECT", "in", LEVELS + ["FRANCE"]),
                                                               ("TIME_PERIOD", "=", y)])
            parts.append(_filter(table.to_pandas(strings_to_categorical=True), dims, mapping))
            del table
    long = pd.concat(parts, ignore_index=True)
    return long.pivot(index=KEY, columns="measure", values="value")


def load(paths):
    wide = None
    for name, dims, mapping in SOURCES:
        part = _read(paths[name], dims, mapping)
        wide = part if wide is None else wide.join(part, how="outer")
    wide = wide.reset_index()
    for col in COLUMNS + ["_commute_motorbike"]:
        if col not in wide.columns:
            wide[col] = float("nan")
    # Deux-roues : publié en 2012, = vélo + deux-roues motorisé ensuite
    wide["commute_two_wheels"] = wide["commute_two_wheels"].fillna(wide["commute_bike"] + wide["_commute_motorbike"])
    return wide[COLUMNS]


def check(wide):
    logger.info("🔎 Lignes par niveau et millésime :")
    for line in wide.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    com = wide[wide.geo_level == "COM"].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    dep = wide[wide.geo_level == "DEP"].set_index(["geo_code", "year"])
    for col in ["unemployed_15_64", "jobs", "workers"]:
        sums = com.groupby(["dep", "year"])[col].sum()
        ecart = (dep[col] - sums.reindex(dep.index)).abs().max()
        logger.info(f"🔎 {col} : écart max département officiel vs somme des communes = {ecart:.6f}")
    fm = wide[wide.geo_level == "FRANCE"].set_index("year")
    rate = (fm["unemployed_15_64"] / fm["active_15_64"] * 100).round(1)
    logger.info("🔎 France métropolitaine, taux de chômage 15-64 ans : " +
                ", ".join(f"{y} = {v} %" for y, v in rate.items()))


def _connect():
    url = make_url(str(engine.url))
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(wide):
    years = sorted(int(y) for y in wide["year"].unique())
    buf = io.StringIO()
    wide.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM employment_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY employment_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE employment_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name, default in DEFAULTS.items():
        parser.add_argument(f"--{name.replace('_', '-')}", dest=name, default=default)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(vars(args))
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
