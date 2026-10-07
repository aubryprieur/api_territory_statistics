"""
Import scolarisation et diplômes INSEE dans education_by_territory, à toutes les échelles
(valeurs officielles INSEE, aucune agrégation côté API) :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources (recensement de la population, millésimes 2012, 2017, 2023) :
  - DS_RP_EDUCATION_PRINC (parquet) : population et population scolarisée par âge et sexe
  - DS_RP_DIPLOMES_PRINC  (parquet) : population de 15 ans ou plus non scolarisée,
                                       par diplôme le plus élevé et sexe
  - DS_RP_TD_EDUCATION_PRINC et DS_RP_TD_POPULATION_AGESEX_PRINC (parquet, tableaux détaillés,
    2023 uniquement) : scolarisés et population par âge fin -> scolarisation à 2 ans et à 3-5 ans.
    Les fichiers complets ou les extraits « _extrait_2-5ans » conviennent.
    Pour 2017, ces 4 colonnes sont reprises de la table schooling_summary (FOR1 2017, communes),
    agrégée par EPCI / département / région via geo_codes. 2012 : non disponible.

Usage :
    python scripts/import_education_by_territory.py              # fichiers par défaut
    python scripts/import_education_by_territory.py --dry-run    # contrôles sans écrire en base
    python scripts/import_education_by_territory.py --education f.parquet --diplomas f.parquet \
        --td-education f.parquet --td-population f.parquet

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
DEFAULT_TD_EDUCATION = "data/education/territory/DS_RP_TD_EDUCATION_PRINC_2023_extrait_2-5ans.parquet"
DEFAULT_TD_POPULATION = "data/education/territory/DS_RP_TD_POPULATION_AGESEX_PRINC_2023_extrait_2-5ans.parquet"
EARLY_COLUMNS = ["pop_2", "enrolled_2", "pop_3_5", "enrolled_3_5"]
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

COLUMNS = KEY + list(EDUCATION_MEASURES.values()) + list(DIPLOMA_MEASURES.values()) + EARLY_COLUMNS


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


def _connect():
    url = make_url(str(engine.url))
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def load_early_2023(td_education_path, td_population_path):
    """Scolarisés et population à 2 ans et 3-5 ans (tableaux détaillés 2023)."""
    group = {"Y2": "2", "Y3": "3_5", "Y4": "3_5", "Y5": "3_5"}
    frames = {}
    for path, prefix, extra in [(td_education_path, "enrolled", {"STUD_AREA": "_T"}),
                                (td_population_path, "pop", {})]:
        logger.info(f"📥 Lecture de {path}")
        cols = ["GEO", "GEO_OBJECT", "TIME_PERIOD", "AGE", "SEX", "OBS_VALUE", *extra]
        df = pd.read_parquet(path, columns=cols)
        keep = df["GEO_OBJECT"].isin(LEVELS) | ((df["GEO_OBJECT"] == "FRANCE") & (df["GEO"] == FRANCE_CODE))
        keep &= df["AGE"].isin(list(group)) & (df["SEX"] == "_T")
        for k, v in extra.items():
            keep &= df[k] == v
        df = df[keep].assign(
            measure=lambda d: prefix + "_" + d["AGE"].map(group),
            year=lambda d: pd.to_datetime(d["TIME_PERIOD"]).dt.year.astype(int),
        )
        frames[prefix] = (df.groupby(["GEO_OBJECT", "GEO", "year", "measure"])["OBS_VALUE"].sum()
                            .unstack("measure"))
    early = frames["enrolled"].join(frames["pop"], how="outer")
    early.index = early.index.set_names(KEY)
    return early


ARM_PATTERN = r"^(751(0[1-9]|1[0-9]|20)|6938[1-9]|132(0[1-9]|1[0-6]))$"
EARLY_2017_SQL = f"""
WITH s AS (
    SELECT geo_code, total_2y AS pop_2, schooled_2y AS enrolled_2,
           total_3_5y AS pop_3_5, schooled_3_5y AS enrolled_3_5,
           geo_code ~ '{ARM_PATTERN}' AS is_arm
    FROM schooling_summary WHERE year = 2017
), com AS (
    SELECT s.*, g.epci, g.dep, g.reg FROM s LEFT JOIN geo_codes g ON g.codgeo = s.geo_code WHERE NOT s.is_arm
)
SELECT 'COM' AS geo_level, geo_code, pop_2, enrolled_2, pop_3_5, enrolled_3_5 FROM com
UNION ALL SELECT 'ARM', geo_code, pop_2, enrolled_2, pop_3_5, enrolled_3_5 FROM s WHERE is_arm
UNION ALL SELECT 'EPCI', epci, sum(pop_2), sum(enrolled_2), sum(pop_3_5), sum(enrolled_3_5) FROM com WHERE epci IS NOT NULL GROUP BY epci
UNION ALL SELECT 'DEP', dep, sum(pop_2), sum(enrolled_2), sum(pop_3_5), sum(enrolled_3_5) FROM com WHERE dep IS NOT NULL GROUP BY dep
UNION ALL SELECT 'REG', reg, sum(pop_2), sum(enrolled_2), sum(pop_3_5), sum(enrolled_3_5) FROM com WHERE reg IS NOT NULL GROUP BY reg
UNION ALL SELECT 'FRANCE', '{FRANCE_CODE}', sum(pop_2), sum(enrolled_2), sum(pop_3_5), sum(enrolled_3_5) FROM com WHERE geo_code NOT LIKE '97%'
"""


def load_early_2017():
    """Scolarisation à 2 ans et 3-5 ans en 2017, depuis schooling_summary (agrégats via geo_codes)."""
    logger.info("📥 Lecture de schooling_summary (2017) en base")
    conn = _connect()
    try:
        df = pd.read_sql(EARLY_2017_SQL, conn)
    finally:
        conn.close()
    df["year"] = 2017
    return df.set_index(KEY)


def load(education_path, diplomas_path, td_education_path=None, td_population_path=None, with_2017=True):
    edu = _read(education_path, ["AGE", "STUD", "SEX"], EDUCATION_MEASURES)
    dip = _read(diplomas_path, ["EDUC", "SEX"], DIPLOMA_MEASURES)
    wide = edu.join(dip, how="outer").reset_index()
    for col in COLUMNS:
        if col not in wide.columns:
            wide[col] = float("nan")
    # Bac+3 ou plus : publié en 2012, = bac+3/4 + bac+5 ou plus ensuite
    computed = wide["bac3_4"] + wide["bac5_plus"]
    wide["bac3_plus"] = wide["bac3_plus"].fillna(computed)

    # Scolarisation à 2 ans et 3-5 ans : 2023 (tableaux détaillés) + 2017 (schooling_summary)
    early_parts = []
    if td_education_path and td_population_path:
        early_parts.append(load_early_2023(td_education_path, td_population_path))
    if with_2017:
        early_parts.append(load_early_2017())
    if early_parts:
        early = pd.concat(early_parts)[EARLY_COLUMNS]
        wide = wide.drop(columns=EARLY_COLUMNS).set_index(KEY).join(early, how="left").reset_index()
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
    for a in ["2", "3_5"]:
        r = (fm[f"enrolled_{a}"] / fm[f"pop_{a}"] * 100).round(1)
        logger.info(f"🔎 France métropolitaine, scolarisation à {a.replace('_', '-')} ans : " +
                    ", ".join(f"{y} = {v} %" for y, v in r.items()))
    filled = wide.dropna(subset=["pop_2"]).groupby(["geo_level", "year"]).size().unstack(fill_value=0)
    logger.info("🔎 Lignes avec scolarisation à 2 ans renseignée : " + filled.to_dict().__repr__())
    rate = (fm["no_diploma"] / fm["non_enrolled_15_plus"] * 100).round(1)
    logger.info("🔎 France métropolitaine, part des sans diplôme : " +
                ", ".join(f"{y} = {v} %" for y, v in rate.items()))


def write(wide):
    years = sorted(int(y) for y in wide["year"].unique())
    buf = io.StringIO()
    wide.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
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
    parser.add_argument("--td-education", default=DEFAULT_TD_EDUCATION)
    parser.add_argument("--td-population", default=DEFAULT_TD_POPULATION)
    parser.add_argument("--without-2017", action="store_true",
                        help="ne pas reprendre la scolarisation à 2 ans / 3-5 ans 2017 depuis schooling_summary")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.education, args.diplomas, args.td_education, args.td_population,
                with_2017=not args.without_2017)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
