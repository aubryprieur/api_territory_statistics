"""
Import scolarisation et diplômes INSEE dans education_by_territory, à toutes les échelles
(valeurs officielles INSEE, aucune agrégation côté API) :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources (recensement de la population, millésimes 2012, 2017, 2023) :
  - DS_RP_EDUCATION_PRINC (parquet) : population et population scolarisée par âge et sexe
  - DS_RP_DIPLOMES_PRINC  (parquet) : population de 15 ans ou plus non scolarisée,
                                       par diplôme le plus élevé et sexe

Usage :
    python scripts/import_education_by_territory.py              # fichiers par défaut
    python scripts/import_education_by_territory.py --dry-run    # contrôles sans écrire en base
    python scripts/import_education_by_territory.py --education f.parquet --diplomas f.parquet

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

DEFAULT_EDUCATION = "data/education/territory/DS_RP_EDUCATION_PRINC_2023.parquet"
DEFAULT_DIPLOMAS = "data/education/territory/DS_RP_DIPLOMES_PRINC_2023.parquet"
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG"]
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]

AGES = {"Y2T5": "2_5", "Y6T10": "6_10", "Y11T14": "11_14", "Y15T17": "15_17",
        "Y18T24": "18_24", "Y25T29": "25_29", "Y_GE30": "30_plus"}
SEXES = {"M": "men", "F": "women"}

# DS_RP_EDUCATION_PRINC : (AGE, STUD, SEX) -> colonne
EDUCATION_MEASURES = {}
for code, age in AGES.items():
    EDUCATION_MEASURES[(code, "_T", "_T")] = f"pop_{age}"
    EDUCATION_MEASURES[(code, "1", "_T")] = f"enrolled_{age}"
    if age in ("15_17", "18_24"):
        for sx, s in SEXES.items():
            EDUCATION_MEASURES[(code, "_T", sx)] = f"pop_{age}_{s}"
            EDUCATION_MEASURES[(code, "1", sx)] = f"enrolled_{age}_{s}"

# DS_RP_DIPLOMES_PRINC : (EDUC, SEX) -> colonne
DIPLOMA_LEVELS = {
    "_T": "non_enrolled_15_plus",
    "001T100_RP": "no_diploma",        # sans diplôme ou CEP
    "200_RP": "bepc",                  # BEPC, brevet des collèges, DNB
    "300_RP": "cap_bep",               # CAP, BEP ou équivalent
    "350T351_RP": "bac",               # bac, brevet professionnel ou équivalent
    "500T702_RP": "higher_education",  # diplôme de l'enseignement supérieur
    "500_RP": "bac2",
    "600_RP": "bac3_4",                # 2017 et 2023
    "700_RP": "bac5_plus",             # 2017 et 2023
    "600T702_RP": "bac3_plus",         # publié tel quel en 2012 ; recalculé (600 + 700) ensuite
}
DIPLOMA_MEASURES = {(e, "_T"): c for e, c in DIPLOMA_LEVELS.items()}
for sx, s in SEXES.items():
    DIPLOMA_MEASURES[("_T", sx)] = f"non_enrolled_15_plus_{s}"
    DIPLOMA_MEASURES[("001T100_RP", sx)] = f"no_diploma_{s}"
    DIPLOMA_MEASURES[("500T702_RP", sx)] = f"higher_education_{s}"

COLUMNS = KEY + list(EDUCATION_MEASURES.values()) + list(DIPLOMA_MEASURES.values())


def _read(path, dims, mapping):
    logger.info(f"📥 Lecture de {path}")
    df = pd.read_parquet(path, columns=["GEO", "GEO_OBJECT", "TIME_PERIOD", *dims, "OBS_VALUE", "OBS_STATUS"])
    keep = df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))
    df = df[keep]
    df = df.assign(measure=[mapping.get(k) for k in zip(*(df[d] for d in dims))])
    df = df[df["measure"].notna()]
    # Statut K = données incluses dans une autre commune (communes fusionnées) -> NULL
    df = df.assign(
        value=pd.to_numeric(df["OBS_VALUE"].where(df["OBS_STATUS"] != "K"), errors="coerce"),
        year=pd.to_datetime(df["TIME_PERIOD"]).dt.year.astype(int),
    )
    return df.rename(columns={"GEO_OBJECT": "geo_level", "GEO": "geo_code"}) \
             .pivot(index=KEY, columns="measure", values="value")


def load(education_path, diplomas_path):
    edu = _read(education_path, ["AGE", "STUD", "SEX"], EDUCATION_MEASURES)
    dip = _read(diplomas_path, ["EDUC", "SEX"], DIPLOMA_MEASURES)
    wide = edu.join(dip, how="outer").reset_index()
    for col in COLUMNS:
        if col not in wide.columns:
            wide[col] = float("nan")
    # Bac+3 ou plus : publié en 2012, = bac+3/4 + bac+5 ou plus ensuite
    computed = wide["bac3_4"] + wide["bac5_plus"]
    wide["bac3_plus"] = wide["bac3_plus"].fillna(computed)
    return wide[COLUMNS]


def check(wide):
    logger.info("🔎 Lignes par niveau et millésime :")
    for line in wide.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    com = wide[wide.geo_level == "COM"].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    dep = wide[wide.geo_level == "DEP"].set_index(["geo_code", "year"])
    for col in ["enrolled_18_24", "no_diploma", "higher_education"]:
        sums = com.groupby(["dep", "year"])[col].sum()
        ecart = (dep[col] - sums.reindex(dep.index)).abs().max()
        logger.info(f"🔎 {col} : écart max département officiel vs somme des communes = {ecart:.6f}")
    fm = wide[wide.geo_level == "FRANCE"].set_index("year")
    rate = (fm["no_diploma"] / fm["non_enrolled_15_plus"] * 100).round(1)
    logger.info("🔎 France métropolitaine, part des sans diplôme : " +
                ", ".join(f"{y} = {v} %" for y, v in rate.items()))


def write(wide):
    url = make_url(str(engine.url))
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
            cur.execute("DELETE FROM education_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY education_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE education_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--education", default=DEFAULT_EDUCATION)
    parser.add_argument("--diplomas", default=DEFAULT_DIPLOMAS)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.education, args.diplomas)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
