"""
Import logement INSEE dans housing_by_territory, à toutes les échelles (valeurs officielles INSEE,
aucune agrégation côté API) :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources (recensement de la population, millésimes 2012, 2017, 2023) :
  - DS_RP_LOGEMENT_PRINC (parquet) : parc de logements (résidences principales, secondaires, vacants ;
    maisons / appartements), résidences principales par nombre de pièces, statut d'occupation,
    ancienneté d'emménagement, combustible principal de chauffage, voitures, stationnement,
    période de construction ; population des ménages
  - DS_RP_LOGEMENT_COMP (parquet) : résidences principales selon l'indicateur de peuplement
    (suroccupation / sous-occupation)

Usage :
    python scripts/import_housing_by_territory.py              # fichiers par défaut
    python scripts/import_housing_by_territory.py --dry-run    # contrôles sans écrire en base

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

DIR = "data/housing/territory"
DEFAULTS = {
    "princ": f"{DIR}/DS_RP_LOGEMENT_PRINC_2023.parquet",
    "comp": f"{DIR}/DS_RP_LOGEMENT_COMP_2023.parquet",
}
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG"]
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]

# --- DS_RP_LOGEMENT_PRINC
PRINC_DIMS = ["RP_MEASURE", "OCS", "L_STAY", "TDW", "NRG_SRC", "CARPARK", "NOR", "TSH", "CARS", "BUILD_END"]


def _p(measure="DWELLINGS", ocs="DW_MAIN", l_stay="_T", tdw="_T", nrg="_T", carpark="_T", nor="_T", tsh="_T",
       cars="_T", build="_T"):
    return (measure, ocs, l_stay, tdw, nrg, carpark, nor, tsh, cars, build)


PRINC = {
    # Parc de logements
    _p(ocs="_T"): "dwellings",
    _p(): "dwellings_main",
    _p(ocs="DW_SEC_DW_OCC"): "dwellings_secondary",
    _p(ocs="DW_VAC"): "dwellings_vacant",
    _p(ocs="_T", tdw="1"): "dwellings_houses",
    _p(ocs="_T", tdw="2"): "dwellings_apartments",
    _p(tdw="1"): "main_houses",
    _p(tdw="2"): "main_apartments",
    # Taille des résidences principales
    _p(nor="R1"): "main_r1",
    _p(nor="R2"): "main_r2",
    _p(nor="R3"): "main_r3",
    _p(nor="R4"): "main_r4",
    _p(nor="R_GE5"): "main_r5p",
    _p(measure="DWELLINGS_ROOMS"): "main_rooms",
    # Statut d'occupation (211 = locataire d'un logement vide non HLM, 212_222 = meublé ou hôtel,
    # 221 = locataire d'un logement HLM vide)
    _p(tsh="100"): "main_owners",
    _p(tsh="200"): "main_tenants",
    _p(tsh="211"): "main_tenants_private",
    _p(tsh="212_222"): "main_tenants_furnished",
    _p(tsh="221"): "main_tenants_social",
    _p(tsh="300"): "main_free",
    # Population des ménages
    _p(measure="DWELLINGS_POPSIZE"): "pop_main",
    _p(measure="DWELLINGS_POPSIZE", tsh="100"): "pop_owners",
    _p(measure="DWELLINGS_POPSIZE", tsh="200"): "pop_tenants",
    _p(measure="DWELLINGS_POPSIZE", tsh="221"): "pop_tenants_social",
    # Ancienneté d'emménagement (ménages)
    _p(l_stay="Y_LT2"): "stay_lt2",
    _p(l_stay="Y2T4"): "stay_2_4",
    _p(l_stay="Y5T9"): "stay_5_9",
    _p(l_stay="Y10T19"): "stay_10_19",
    _p(l_stay="Y20T29"): "stay_20_29",
    _p(l_stay="Y_GE30"): "stay_ge30",
    # Ancienneté totale d'emménagement (somme des années, pour la moyenne)
    _p(measure="DWELLING_L_STAY"): "stay_years",
    _p(measure="DWELLING_L_STAY", tsh="100"): "stay_years_owners",
    _p(measure="DWELLING_L_STAY", tsh="200"): "stay_years_tenants",
    _p(measure="DWELLING_L_STAY", tsh="221"): "stay_years_social",
    # Combustible principal de chauffage
    _p(nrg="TOWN_GAS"): "heat_town_gas",
    _p(nrg="OIL"): "heat_oil",
    _p(nrg="ELC"): "heat_electric",
    _p(nrg="BOT_GAS"): "heat_bottled_gas",
    _p(nrg="OTH"): "heat_other",
    # Voitures et stationnement
    _p(carpark="1"): "with_parking",
    _p(cars="C0"): "cars_0",
    _p(cars="C1"): "cars_1",
    _p(cars="C_GE2"): "cars_2p",
    # Période de construction (achevées avant le recensement - 2 ans)
    _p(build="Y_LT1919"): "built_lt1919",
    _p(build="Y1919T1945"): "built_1919_1945",
    _p(build="Y1946T1970"): "built_1946_1970",
    _p(build="Y1971T1990"): "built_1971_1990",
    _p(build="Y1991T2005"): "built_1991_2005",
    _p(build="Y2006TAAAA"): "built_2006_plus",
    _p(build="Y_LT1946"): "_built_lt1946",      # 2012 uniquement
    _p(build="Y1946T1990"): "_built_1946_1990",  # 2012 uniquement
    _p(build="Y1991T2009"): "_built_1991_2009",  # 2012 uniquement
    _p(build="Y_LT2010"): "_built_known",        # 2012
    _p(build="Y_LT2015"): "_built_known",        # 2017
    _p(build="Y_LT2021"): "_built_known",        # 2023
}

# --- DS_RP_LOGEMENT_COMP : indicateur de peuplement des résidences principales
COMP_DIMS = ["OCS", "RP_MEASURE", "OCC_IND"]
COMP = {
    ("DW_MAIN", "DWELLINGS", "_T"): "occ_total",
    ("DW_MAIN", "DWELLINGS", "SEV_OVER_OCC"): "occ_over_severe",
    ("DW_MAIN", "DWELLINGS", "MOD_OVER_OCC"): "occ_over_moderate",
    ("DW_MAIN", "DWELLINGS", "STD_OCC"): "occ_standard",
    ("DW_MAIN", "DWELLINGS", "MOD_UNDER_OCC"): "occ_under_moderate",
    ("DW_MAIN", "DWELLINGS", "SEV_UNDER_OCC"): "occ_under_severe",
    ("DW_MAIN", "DWELLINGS", "VSEV_UNDER_OCC"): "occ_under_very_severe",
}

SOURCES = [("princ", PRINC_DIMS, PRINC), ("comp", COMP_DIMS, COMP)]
# Périodes de construction harmonisées entre millésimes (2012 n'a que 3 grandes périodes)
BUILT_GROUPS = ["built_before_1946", "built_1946_1990", "built_after_1990", "built_known"]
COLUMNS = KEY + list(dict.fromkeys(c for _, _, m in SOURCES for c in m.values() if not c.startswith("_"))) + BUILT_GROUPS


def _filter(df, dims, mapping):
    keep = df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))
    df = df[keep]
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
    """Lecture année par année, filtrée sur les niveaux utiles : limite la mémoire nécessaire."""
    import pyarrow.parquet as pq
    logger.info(f"📥 Lecture de {path}")
    cols = ["GEO", "GEO_OBJECT", "TIME_PERIOD", *dims, "OBS_VALUE", "OBS_STATUS"]
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
    raw = [c for _, _, m in SOURCES for c in m.values()]
    for col in raw:
        if col not in wide.columns:
            wide[col] = float("nan")
    # Périodes harmonisées : 2012 publie directement les grandes périodes, 2017 et 2023 le détail
    wide["built_before_1946"] = wide["_built_lt1946"].fillna(wide["built_lt1919"] + wide["built_1919_1945"])
    wide["built_1946_1990"] = wide["_built_1946_1990"].fillna(wide["built_1946_1970"] + wide["built_1971_1990"])
    wide["built_after_1990"] = wide["_built_1991_2009"].fillna(wide["built_1991_2005"] + wide["built_2006_plus"])
    wide["built_known"] = wide["_built_known"]
    return wide[COLUMNS]


def check(wide):
    logger.info("🔎 Lignes par niveau et millésime :")
    for line in wide.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    com = wide[wide.geo_level == "COM"].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    dep = wide[wide.geo_level == "DEP"].set_index(["geo_code", "year"])
    for col in ["dwellings", "main_tenants_social", "occ_over_severe"]:
        sums = com.groupby(["dep", "year"])[col].sum()
        ecart = (dep[col] - sums.reindex(dep.index)).abs().max()
        logger.info(f"🔎 {col} : écart max département officiel vs somme des communes = {ecart:.6f}")
    gap_park = (wide["dwellings_main"] + wide["dwellings_secondary"] + wide["dwellings_vacant"]
                - wide["dwellings"]).abs().max()
    gap_tsh = (wide["main_owners"] + wide["main_tenants"] + wide["main_free"] - wide["dwellings_main"]).abs().max()
    # Peuplement (exploitation complémentaire) vs résidences principales (principale), hors communes
    big = wide[wide.geo_level != "COM"]
    gap_occ = (big["occ_total"] - big["dwellings_main"]).abs() / big["dwellings_main"]
    logger.info(f"🔎 Cohérence : résid. princ. + secondaires + vacants - logements = {gap_park:.6f} ; "
                f"propriétaires + locataires + logés gratuitement - résid. princ. = {gap_tsh:.6f} ; "
                f"peuplement vs résid. princ. (hors communes) : écart relatif max = {gap_occ.max():.4%}")
    fm = wide[wide.geo_level == "FRANCE"].set_index("year")
    for label, num, den in [("logements vacants", "dwellings_vacant", "dwellings"),
                            ("locataires HLM", "main_tenants_social", "dwellings_main"),
                            ("suroccupation", None, "occ_total")]:
        n = fm["occ_over_severe"] + fm["occ_over_moderate"] if num is None else fm[num]
        rate = (n / fm[den] * 100).round(1)
        logger.info(f"🔎 France métropolitaine, {label} : " + ", ".join(f"{y} = {v} %" for y, v in rate.items()))


def _connect():
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
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
            cur.execute("DELETE FROM housing_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY housing_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE housing_by_territory")
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
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
