"""
Import population INSEE dans deux tables, à toutes les échelles (valeurs officielles INSEE,
aucune agrégation côté API) : COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

1) population_by_territory — millésimes 2012, 2017, 2023
  - DS_RP_POPULATION_PRINC (parquet) : population par grande tranche d'âge et sexe
  - DS_RP_POPULATION_COMP  (parquet) : population de 15 ans ou plus par catégorie socioprofessionnelle
  - DS_RP_MIGRES_PRINC     (parquet) : lieu de résidence un an auparavant (mobilité résidentielle)
  - extrait de DS_RP_TD_POPULATION_AGESEX_PRINC (2023) : pyramide des âges par tranche de 5 ans
    et sexe, tranches de l'enfance et de la jeunesse (0-2, 3-5, 6-10, 11-14, 15-17, 18-24 ans)

2) population_history_by_territory — recensements 1968, 1975, 1982, 1990, 1999, 2007, 2012, 2017, 2023
  - DS_RP_SERIE_HISTORIQUE (csv) : population, naissances et décès cumulés entre deux recensements,
    logements ; superficie (2023)

Usage :
    python scripts/import_population_by_territory.py              # fichiers par défaut
    python scripts/import_population_by_territory.py --dry-run    # contrôles sans écrire en base

Nécessite pyarrow (pip install pyarrow). Les millésimes présents remplacent ceux déjà en base.
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/population/territory"
DEFAULTS = {
    "princ": f"{DIR}/DS_RP_POPULATION_PRINC_2023.parquet",
    "comp": f"{DIR}/DS_RP_POPULATION_COMP_2023.parquet",
    "migres": f"{DIR}/DS_RP_MIGRES_PRINC_2023.parquet",
    "pyramide": f"{DIR}/DS_RP_TD_POPULATION_AGESEX_PRINC_2023_extrait_pyramide.parquet",
    "historique": f"{DIR}/DS_RP_SERIE_HISTORIQUE_2023_data.csv",
}
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG"]
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]
SEXES = {"_T": "", "F": "_women", "M": "_men"}

# --- DS_RP_POPULATION_PRINC : (AGE, SEX) -> colonne
AGES = {"_T": "pop", "Y_LT15": "pop_lt15", "Y15T24": "pop_15_24", "Y25T39": "pop_25_39", "Y40T54": "pop_40_54",
        "Y55T64": "pop_55_64", "Y65T79": "pop_65_79", "Y_GE80": "pop_ge80", "Y_GE65": "pop_ge65",
        "Y_LT20": "pop_lt20", "Y20T64": "pop_20_64"}
PRINC = {(ag, sx): f"{name}{s}" for ag, name in AGES.items() for sx, s in SEXES.items()}

# --- DS_RP_POPULATION_COMP : (AGE, SEX, PCS) -> colonne (15 ans ou plus ; 7 = retraités, 9 = autres sans activité)
COMP = {("Y_GE15", "_T", "_T"): "pop_15p"}
for p in ["1", "2", "3", "4", "5", "6", "7", "9"]:
    COMP[("Y_GE15", "_T", p)] = f"pcs_{p}"

# --- DS_RP_MIGRES_PRINC : (AGE, PREV_RES_AREA) -> colonne (population d'un an ou plus)
MIGRES = {
    ("Y_GE1", "_T"): "mig_total",
    ("Y_GE1", "11"): "mig_same_dwelling",
    ("Y_GE1", "12"): "mig_same_commune",
    ("Y_GE1", "20_30"): "mig_other_commune",
    ("Y_GE1", "21"): "mig_same_department",
    ("Y_GE1", "22"): "mig_same_region",
    ("Y_GE1", "23"): "mig_other_region",
    ("Y_GE1", "24"): "mig_overseas",
    ("Y_GE1", "25T32"): "mig_abroad",
}
for ag, a in {"Y1T14": "1_14", "Y15T24": "15_24", "Y25T54": "25_54", "Y_GE55": "ge55"}.items():
    MIGRES[(ag, "20_30")] = f"mig_other_commune_{a}"

# --- Extrait TD_POPULATION_AGESEX (2023) : (AGE, SEX) -> colonne
PYRAMID_GROUPS = [f"{a}_{a + 4}" for a in range(0, 95, 5)] + ["ge95"]
PYRAMIDE = {}
for g in PYRAMID_GROUPS:
    code = "Y_GE95" if g == "ge95" else "Y" + g.replace("_", "T")
    PYRAMIDE[(code, "M")] = f"pyr_men_{g}"
    PYRAMIDE[(code, "F")] = f"pyr_women_{g}"
for code, name in {"Y0T2": "age_0_2", "Y3T5": "age_3_5", "Y6T10": "age_6_10", "Y11T14": "age_11_14",
                   "Y15T17": "age_15_17", "Y18T24": "age_18_24"}.items():
    PYRAMIDE[(code, "_T")] = name

SOURCES = [
    ("princ", ["AGE", "SEX"], PRINC),
    ("comp", ["AGE", "SEX", "PCS"], COMP),
    ("migres", ["AGE", "PREV_RES_AREA"], MIGRES),
    ("pyramide", ["AGE", "SEX"], PYRAMIDE),
]
COLUMNS = KEY + [c for _, _, m in SOURCES for c in m.values()]

# --- DS_RP_SERIE_HISTORIQUE : (RP_MEASURE, OCS) -> colonne
HISTORY = {
    ("POP", "_T"): "population",
    ("BRTH", "_T"): "births",       # naissances cumulées depuis le recensement précédent
    ("DEATH", "_T"): "deaths",      # décès cumulés depuis le recensement précédent
    ("DWELLINGS", "_T"): "dwellings",
    ("DWELLINGS", "DW_MAIN"): "dwellings_main",
    ("DWELLINGS", "DW_SEC_DW_OCC"): "dwellings_secondary",
    ("DWELLINGS", "DW_VAC"): "dwellings_vacant",
    ("DWELLINGS_POPSIZE", "DW_MAIN"): "households_population",
    ("SUP", "_T"): "area_km2",      # 2023 uniquement
}
HISTORY_COLUMNS = KEY + list(HISTORY.values())


def _keep_levels(df):
    return df[df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))]


def _to_long(df, dims, mapping):
    df = _keep_levels(df)
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


def _read_parquet(path, dims, mapping):
    """Lecture année par année, filtrée sur les niveaux utiles : limite la mémoire nécessaire."""
    import pyarrow.parquet as pq
    logger.info(f"📥 Lecture de {path}")
    cols = ["GEO", "GEO_OBJECT", "TIME_PERIOD", *dims, "OBS_VALUE", "OBS_STATUS"]
    years = pq.read_table(path, columns=["TIME_PERIOD"]).column(0).unique().to_pylist()
    parts = []
    for y in sorted(years):
        table = pq.read_table(path, columns=cols, filters=[("GEO_OBJECT", "in", LEVELS + ["FRANCE"]),
                                                           ("TIME_PERIOD", "=", y)])
        parts.append(_to_long(table.to_pandas(strings_to_categorical=True), dims, mapping))
        del table
    long = pd.concat(parts, ignore_index=True)
    return long.pivot(index=KEY, columns="measure", values="value")


def load(paths):
    wide = None
    for name, dims, mapping in SOURCES:
        part = _read_parquet(paths[name], dims, mapping)
        wide = part if wide is None else wide.join(part, how="outer")
    wide = wide.reset_index()
    for col in COLUMNS:
        if col not in wide.columns:
            wide[col] = float("nan")
    return wide[COLUMNS]


def load_history(path):
    logger.info(f"📥 Lecture de {path}")
    cols = ["GEO", "GEO_OBJECT", "RP_MEASURE", "OCS", "OBS_STATUS", "TIME_PERIOD", "OBS_VALUE"]
    parts = [_to_long(chunk, ["RP_MEASURE", "OCS"], HISTORY) for chunk in
             pd.read_csv(path, sep=";", dtype=str, usecols=cols, keep_default_na=False, chunksize=500_000)]
    long = pd.concat(parts, ignore_index=True)
    wide = long.pivot(index=KEY, columns="measure", values="value").reset_index()
    for col in HISTORY_COLUMNS:
        if col not in wide.columns:
            wide[col] = float("nan")
    # Pas de naissances ni de décès « avant 1968 » : la série commence en 1968
    wide.loc[wide["year"] == wide["year"].min(), ["births", "deaths"]] = float("nan")
    return wide[HISTORY_COLUMNS]


def _dep(codes):
    return codes.str[:3].where(codes.str.startswith("97"), codes.str[:2])


def check(wide, hist):
    logger.info("🔎 population_by_territory, lignes par niveau et millésime :")
    for line in wide.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    com = wide[wide.geo_level == "COM"].copy()
    com["dep"] = _dep(com.geo_code)
    dep = wide[wide.geo_level == "DEP"].set_index(["geo_code", "year"])
    for col in ["pop", "pop_ge65", "pcs_6", "mig_other_commune", "pyr_women_80_84"]:
        sums = com.groupby(["dep", "year"])[col].sum(min_count=1)
        ecart = (dep[col] - sums.reindex(dep.index)).abs().max()
        logger.info(f"🔎 {col} : écart max département officiel vs somme des communes = {ecart:.6f}")
    pyr = wide[[c for c in COLUMNS if c.startswith("pyr_")]].sum(axis=1, min_count=1)
    gap = ((pyr - wide["pop"]).abs() / wide["pop"])[wide.year == 2023]
    logger.info(f"🔎 Pyramide 2023 : somme des tranches vs population, écart relatif max = {gap.max():.6%}")
    fm = wide[wide.geo_level == "FRANCE"].set_index("year")
    logger.info("🔎 France métropolitaine, population : " + ", ".join(f"{y} = {v:,.0f}" for y, v in fm["pop"].items()))
    logger.info("🔎 France métropolitaine, indice de vieillissement (65 ans ou + pour 100 moins de 20 ans) : " +
                ", ".join(f"{y} = {v:.1f}" for y, v in (fm["pop_ge65"] / fm["pop_lt20"] * 100).items()))

    logger.info("🔎 population_history_by_territory, lignes par niveau et recensement :")
    for line in hist.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    hfm = hist[hist.geo_level == "FRANCE"].set_index("year")["population"]
    logger.info("🔎 France métropolitaine, population historique : " +
                ", ".join(f"{y} = {v / 1e6:.1f} M" for y, v in hfm.items()))
    # La série historique est recalculée en géographie 2026 : quelques communes aux limites modifiées diffèrent
    both = hist.merge(wide[KEY + ["pop"]], on=KEY)
    diff = both[(both["population"] - both["pop"]).abs() > 1]
    logger.info(f"🔎 Série historique vs population 2012-2017-2023 : {len(diff)} écarts (communes aux limites "
                f"modifiées), aucun au-delà des communes : {diff.geo_level.eq('COM').all()}")


def _connect():
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(table, df, columns):
    years = sorted(int(y) for y in df["year"].unique())
    buf = io.StringIO()
    df[columns].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table} WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {table} : {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {table} : {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"ANALYZE {table}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name, default in DEFAULTS.items():
        parser.add_argument(f"--{name}", dest=name, default=default)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(vars(args))
    history = load_history(args.historique)
    check(data, history)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write("population_by_territory", data, COLUMNS)
        write("population_history_by_territory", history, HISTORY_COLUMNS)
        logger.info("🏁 Import terminé")
