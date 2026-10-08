"""
Import revenus et pauvreté (INSEE, Filosofi) dans revenues_by_territory, à toutes les échelles :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources :
  - Filosofi 2017 à 2021, « chiffres clés » (data/revenues/<niveau>/cc_filosofi_<année>_<NIVEAU>.csv) :
    niveau de vie médian, taux de pauvreté (global, par âge du référent fiscal, par statut d'occupation),
    D1, D9, rapport interdécile, part des ménages imposés, structure du revenu disponible.
    Communes : détail publié au-delà de 1 000 ménages / 2 000 personnes environ (sinon « s »).
  - Filosofi 2023 (data/revenues/filosofi_2023/) :
      DS_FILOSOFI_CC_2023 : niveau de vie médian et taux de pauvreté pour les communes et EPCI ;
        détail complet (déciles, Gini, S80/S20, structure du revenu) pour départements, régions, France ;
      DS_FILOSOFI_SAGE_LOG_TP_NIVVIE_2023 : taux de pauvreté et médiane par âge des individus et par
        statut d'occupation du logement (départements, régions, France).
  Pas de millésime 2022 dans ces fichiers.

Usage :
    python scripts/import_revenues_by_territory.py              # fichiers par défaut
    python scripts/import_revenues_by_territory.py --dry-run    # contrôles sans écrire en base
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

DIR = "data/revenues"
OLD_YEARS = [2017, 2018, 2019, 2020, 2021]
OLD_LEVELS = {  # dossier, suffixe de fichier, geo_level
    "commune": ("COM", "COM"), "epci": ("EPCI", "EPCI"), "department": ("DEP", "DEP"),
    "region": ("REG", "REG"), "france": ("METRO", "FRANCE"),
}
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]
ARM_PREFIXES = ("751", "6938", "132")

# Chiffres clés 2017-2021 : préfixe de variable (suffixé par l'année sur 2 chiffres) -> colonne
OLD_VARS = {
    "NBMENFISC": "fiscal_households", "NBPERSMENFISC": "fiscal_persons", "MED": "median_living_standard",
    "PIMP": "taxed_households_rate", "TP60": "poverty_rate",
    "TP60AGE1": "poverty_rate_ref_lt30", "TP60AGE2": "poverty_rate_ref_30_39", "TP60AGE3": "poverty_rate_ref_40_49",
    "TP60AGE4": "poverty_rate_ref_50_59", "TP60AGE5": "poverty_rate_ref_60_74", "TP60AGE6": "poverty_rate_ref_ge75",
    "TP60TOL1": "poverty_rate_owners", "TP60TOL2": "poverty_rate_tenants",
    "PACT": "share_activity_income", "PTSA": "share_salaries", "PCHO": "share_unemployment_benefits",
    "PBEN": "share_self_employment", "PPEN": "share_pensions", "PPAT": "share_property_income",
    "PPSOC": "share_social_benefits", "PPFAM": "share_family_benefits", "PPMINI": "share_minimum_income",
    "PPLOGT": "share_housing_benefits", "PIMPOT": "share_taxes",
    "D1": "d1", "D9": "d9", "RD": "interdecile_ratio",
}
# Filosofi 2023 : mesure -> colonne
NEW_VARS = {
    "MED_SL": "median_living_standard", "PR_MD60": "poverty_rate",
    "D1_SL": "d1", "D2_SL": "d2", "D3_SL": "d3", "D4_SL": "d4", "D6_SL": "d6", "D7_SL": "d7", "D8_SL": "d8",
    "D9_SL": "d9", "Q1_SL": "q1", "Q3_SL": "q3", "IR_D9_D1_SL": "interdecile_ratio", "GI_SL": "gini",
    "S80S20_SL": "s80s20", "IQR_SL": "interquartile_range",
    "S_EI_DI": "share_activity_income", "S_EI_DI_SAL": "share_salaries", "S_EI_DI_UNE": "share_unemployment_benefits",
    "S_EI_DI_N_SAL": "share_self_employment", "S_RET_PEN_DI": "share_pensions",
    "S_INC_ASS_DI": "share_property_income", "S_SOC_BEN_DI": "share_social_benefits",
    "S_SOC_BEN_DI_FAM_BEN": "share_family_benefits", "S_SOC_BEN_DI_MIN_SOC": "share_minimum_income",
    "S_SOC_BEN_DI_HOU_BEN": "share_housing_benefits", "S_DIR_TAX_DI": "share_taxes",
}
# Filosofi 2023 par âge des individus et statut d'occupation : (AGE_GP, TSH) -> suffixe
SAGE = {("Y_LT18", "_T"): "lt18", ("Y18T29", "_T"): "18_29", ("Y30T39", "_T"): "30_39", ("Y40T49", "_T"): "40_49",
        ("Y50T64", "_T"): "50_64", ("Y65T74", "_T"): "65_74", ("Y_GE75", "_T"): "ge75"}
VALUE_COLUMNS = list(dict.fromkeys(
    list(OLD_VARS.values()) + list(NEW_VARS.values())
    + [f"poverty_rate_ind_{a}" for a in SAGE.values()] + [f"median_ind_{a}" for a in SAGE.values()]))
COLUMNS = KEY + VALUE_COLUMNS


def _num(series):
    return pd.to_numeric(series.astype(str).str.strip().str.replace(",", ".", regex=False)
                         .replace({"s": None, "": None, "nd": None, "nan": None}), errors="coerce")


def _code(level, codes):
    c = codes.astype(str).str.strip()
    if level in ("COM", "ARM"):
        return c.str.zfill(5)
    if level == "DEP":
        return c.where(c.str.len() > 1, c.str.zfill(2))
    if level == "REG":
        return c.str.zfill(2)
    return c


def load_old(d=DIR):
    frames = []
    for folder, (suffix, level) in OLD_LEVELS.items():
        for year in OLD_YEARS:
            path = os.path.join(d, folder, f"cc_filosofi_{year}_{suffix}.csv")
            if not os.path.exists(path):
                logger.warning(f"⚠️ fichier absent : {path}")
                continue
            raw = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
            yy = str(year)[2:]
            out = pd.DataFrame({"geo_level": [level] * len(raw), "year": [year] * len(raw)})
            out["geo_code"] = FRANCE_CODE if level == "FRANCE" else _code(level, raw["CODGEO"]).values
            for var, col in OLD_VARS.items():
                src = f"{var}{yy}"
                out[col] = _num(raw[src]).values if src in raw.columns else float("nan")
            if level == "COM":
                out.loc[out["geo_code"].str.startswith(ARM_PREFIXES) & (out["geo_code"] != "13200"), "geo_level"] = "ARM"
            frames.append(out)
    return pd.concat(frames, ignore_index=True)


def load_2023(d=DIR):
    base = os.path.join(d, "filosofi_2023")
    cc = pd.read_csv(os.path.join(base, "DS_FILOSOFI_CC_2023_data.csv"), sep=";", dtype=str)
    cc = cc[cc["GEO_OBJECT"].isin(["COM", "ARM", "EPCI", "DEP", "REG"])
            | ((cc["GEO_OBJECT"] == "FRANCE") & (cc["GEO"] == FRANCE_CODE))]
    cc = cc[cc["FILOSOFI_MEASURE"].isin(NEW_VARS)]
    cc = cc.assign(value=_num(cc["OBS_VALUE"]), measure=cc["FILOSOFI_MEASURE"].map(NEW_VARS),
                   geo_level=cc["GEO_OBJECT"], geo_code=cc["GEO"].str.strip(), year=2023)
    wide = cc.pivot_table(index=KEY, columns="measure", values="value", aggfunc="first")

    sage_path = os.path.join(base, "DS_FILOSOFI_SAGE_LOG_TP_NIVVIE_2023_data.csv")
    if os.path.exists(sage_path):
        s = pd.read_csv(sage_path, sep=";", dtype=str)
        s = s[(s["SEX"] == "_T") & (s["GEO_OBJECT"].isin(["DEP", "REG"])
                                    | ((s["GEO_OBJECT"] == "FRANCE") & (s["GEO"] == FRANCE_CODE)))]
        keymap = {"|".join(k): v for k, v in SAGE.items()}
        keymap.update({"_T|1": "owners", "_T|2": "tenants"})
        suffix = (s["AGE_GP"] + "|" + s["TSH"]).map(keymap)
        s = s[suffix.notna()].assign(suffix=suffix[suffix.notna()])
        prefix = s["FILOSOFI_MEASURE"].map({"PR_MD60": "poverty_rate", "MED_SL": "median"})
        col = prefix + "_" + s["suffix"].where(s["suffix"].isin(["owners", "tenants"]), "ind_" + s["suffix"])
        col = col.where(~col.isin(["median_owners", "median_tenants"]))  # médianes par statut : non retenues
        s = s.assign(measure=col, value=_num(s["OBS_VALUE"]), geo_level=s["GEO_OBJECT"],
                     geo_code=s["GEO"].str.strip(), year=2023).dropna(subset=["measure"])
        wide = wide.join(s.pivot_table(index=KEY, columns="measure", values="value", aggfunc="first"), how="outer")
    wide = wide.reset_index()
    wide["geo_code"] = [_code(l, pd.Series([c])).iloc[0] if l != "FRANCE" else FRANCE_CODE
                        for l, c in zip(wide["geo_level"], wide["geo_code"])]
    return wide


def load(d=DIR):
    data = pd.concat([load_old(d), load_2023(d)], ignore_index=True)
    for col in COLUMNS:
        if col not in data.columns:
            data[col] = float("nan")
    data = data.drop_duplicates(KEY, keep="last")
    return data[COLUMNS].sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau et année :")
    for line in data.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    logger.info("🔎 Communes avec taux de pauvreté publié : " + ", ".join(
        f"{y} = {n}" for y, n in data[data.geo_level == "COM"].groupby("year")["poverty_rate"].count().items()))
    fm = data[data.geo_level == "FRANCE"].set_index("year")
    logger.info("🔎 France métropolitaine, niveau de vie médian : " +
                ", ".join(f"{y} = {v:,.0f} €" for y, v in fm["median_living_standard"].items()))
    logger.info("🔎 France métropolitaine, taux de pauvreté : " +
                ", ".join(f"{y} = {v} %" for y, v in fm["poverty_rate"].items()))
    gap = (data["share_salaries"] + data["share_unemployment_benefits"] + data["share_self_employment"]
           - data["share_activity_income"]).abs()
    logger.info(f"🔎 Salaires + chômage + non-salariés - revenus d'activité : écart max = {gap.max():.2f} pt")


def _connect():
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(data):
    years = sorted(int(y) for y in data["year"].unique())
    buf = io.StringIO()
    data.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM revenues_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY revenues_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE revenues_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier data/revenues")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.dir)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
