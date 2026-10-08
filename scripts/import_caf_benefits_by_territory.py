"""
Import des allocataires et bénéficiaires des prestations CAF (Cnaf, data.caf.fr) dans
caf_benefits_by_territory, au 31 décembre de 2020 à 2024 :
    COM, ARM, EPCI, DEP (fichiers Cnaf) ; REG et FRANCE ('FM' = France métropolitaine)
    obtenus par somme des départements (la Cnaf ne publie pas les régions).

Sources (data.caf.fr, « Foyers allocataires et personnes couvertes par prestation ») :
  - s_ben_com_f.parquet  : communes de domicile, décembre 2020-2024 (effectifs arrondis à 5)
  - s_ben_epci_f.parquet : EPCI, décembre 2020-2024 (arrondis à 5)
  - s_ben_dep.parquet    : départements, mensuel 2016-2026 (on retient décembre)
Pour chaque prestation : foyers allocataires (indfoy), personnes couvertes (indnbp, allocataire,
conjoint, enfants et autres personnes à charge), montant mensuel versé (indmtt) ; bénéficiaires
(indben) pour l'AAH et l'AEEH. Les communes n'ont pas les prestations liées au handicap.

Usage :
    python scripts/import_caf_benefits_by_territory.py              # fichiers par défaut
    python scripts/import_caf_benefits_by_territory.py --dry-run    # contrôles sans écrire en base
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

DIR = "data/caf_benefits"
FILES = {"com": "s_ben_com_f.parquet", "epci": "s_ben_epci_f.parquet", "dep": "s_ben_dep.parquet"}
YEARS = range(2020, 2025)
FRANCE_CODE = "FM"
KEY = ["geo_level", "geo_code", "year"]
ARM_PREFIXES = ("751", "6938", "132")

# Prestation CAF -> nom de colonne
BENEFITS = {
    "ndur": "all",              # toutes prestations (au moins un droit versable)
    "ndurpaje": "paje",         # prestation d'accueil du jeune enfant (ensemble)
    "ab": "paje_basic",         # allocation de base de la Paje
    "cmg": "cmg",               # complément de libre choix du mode de garde
    "prepare": "prepare",       # prestation partagée d'éducation de l'enfant
    "ndurej": "children",       # prestations enfance et jeunesse (ensemble)
    "af": "af",                 # allocations familiales
    "cf": "cf",                 # complément familial
    "ars": "ars",               # allocation de rentrée scolaire
    "asf": "asf",               # allocation de soutien familial
    "ndurhd": "disability",     # prestations handicap (ensemble) — hors communes
    "aah": "aah",               # allocation aux adultes handicapés — hors communes
    "aeeh": "aeeh",             # allocation d'éducation de l'enfant handicapé — hors communes
    "ndural": "housing",        # aides au logement (ensemble)
    "apl": "apl",               # aide personnalisée au logement
    "alf": "alf",               # allocation de logement familiale
    "als": "als",               # allocation de logement sociale
    "ndurins": "insertion",     # revenu de solidarité active et prime d'activité (ensemble)
    "rsa": "rsa",               # revenu de solidarité active
    "ppa": "ppa",               # prime d'activité
}
MEASURES = {"indfoy": "households", "indnbp": "persons", "indmtt": "amount"}
SOURCE_COLUMNS = {f"{m}_{b}": f"{name}_{mname}" for b, name in BENEFITS.items() for m, mname in MEASURES.items()}
SOURCE_COLUMNS.update({"indben_aah": "aah_beneficiaries", "indben_aeeh": "aeeh_beneficiaries"})
COLUMNS = KEY + list(SOURCE_COLUMNS.values())


def _prepare(df, level, code_col):
    df = df.copy()
    dt = pd.to_datetime(df["dtreffre"].astype(str))
    df = df[(dt.dt.month == 12) & dt.dt.year.isin(YEARS)]
    df["year"] = pd.to_datetime(df["dtreffre"].astype(str)).dt.year
    df["geo_code"] = df[code_col].astype(str).str.strip()
    df = df[~df["geo_code"].isin(["XX", "99", "nan", "None"]) & df[code_col].notna()]
    df["geo_level"] = level
    if level == "COM":
        df["geo_code"] = df["geo_code"].str.zfill(5)
        df.loc[df["geo_code"].str.startswith(ARM_PREFIXES) & (df["geo_code"] != "13200"), "geo_level"] = "ARM"
    if level == "DEP":
        df["geo_code"] = df["geo_code"].where(df["geo_code"].str.len() > 1, df["geo_code"].str.zfill(2))
    # Doublons de la source (lignes techniques à 1 foyer, EPCI répétés) : on garde la ligne la plus complète
    df = df.sort_values("indfoy_ndur").drop_duplicates(["geo_level", "geo_code", "year"], keep="last")
    for src in SOURCE_COLUMNS:
        if src not in df.columns:
            df[src] = float("nan")
    out = df[["geo_level", "geo_code", "year", *SOURCE_COLUMNS]].rename(columns=SOURCE_COLUMNS)
    # Certaines colonnes sont publiées en texte (ex. indben_aeeh des départements) : conversion numérique,
    # sinon la somme régionale concatène les chaînes
    values = list(SOURCE_COLUMNS.values())
    out[values] = out[values].apply(pd.to_numeric, errors="coerce")
    return out, df


def load(d=DIR):
    parts = []
    com, _ = _prepare(pd.read_parquet(os.path.join(d, FILES["com"])), "COM", "numcomdo")
    epci, _ = _prepare(pd.read_parquet(os.path.join(d, FILES["epci"])), "EPCI", "numepci")
    dep, dep_raw = _prepare(pd.read_parquet(os.path.join(d, FILES["dep"])), "DEP", "numdep")
    parts += [com, epci, dep]

    # Régions et France métropolitaine : somme des départements (effectifs et montants additifs)
    values = [c for c in COLUMNS if c not in KEY]
    reg_of = dep_raw.set_index(["geo_code", "year"])["numregi"].astype(str)
    dep_r = dep.set_index(["geo_code", "year"]).join(reg_of.rename("reg")).reset_index()
    dep_r = dep_r[~dep_r["reg"].isin(["XX", "nan"])]
    reg = dep_r.groupby(["reg", "year"])[values].sum(min_count=1).reset_index().rename(columns={"reg": "geo_code"})
    reg["geo_level"] = "REG"
    metro = dep[~dep["geo_code"].str.startswith("97")]
    fm = metro.groupby("year")[values].sum(min_count=1).reset_index()
    fm["geo_level"], fm["geo_code"] = "FRANCE", FRANCE_CODE
    parts += [reg, fm]
    data = pd.concat(parts, ignore_index=True)
    return data[COLUMNS].sort_values(KEY).reset_index(drop=True)


def check(data, d=DIR):
    logger.info("🔎 Lignes par niveau et année :")
    for line in data.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    com = data[data.geo_level.isin(["COM", "ARM"])].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    dep = data[data.geo_level == "DEP"].set_index(["geo_code", "year"])
    for col in ["all_households", "rsa_households", "housing_households"]:
        sums = com.groupby(["dep", "year"])[col].sum()
        rel = ((dep[col] - sums.reindex(dep.index)).abs() / dep[col]).dropna()
        logger.info(f"🔎 {col} : écart relatif médian département vs somme des communes = {rel.median():.2%} "
                    f"(max {rel.max():.2%}, effectifs communaux arrondis à 5)")
    nat_path = os.path.join(d, "s_ben_nat.parquet")
    if os.path.exists(nat_path):
        nat = pd.read_parquet(nat_path)
        nat = nat[nat["dtreffre"].astype(str).str.endswith("12-01")]
        nat["year"] = nat["dtreffre"].astype(str).str[:4].astype(int)
        nat = nat.set_index("year")["indfoy_ndur"]
        alldep = data[data.geo_level == "DEP"].groupby("year")["all_households"].sum()
        logger.info("🔎 Foyers allocataires, somme des départements vs France entière : " +
                    ", ".join(f"{y} : {alldep.get(y, 0):,.0f} / {v:,.0f}" for y, v in nat.items() if y in YEARS))
    fm = data[data.geo_level == "FRANCE"].set_index("year")
    logger.info("🔎 France métropolitaine, bénéficiaires de l'AEEH : " +
                ", ".join(f"{y} = {v:,.0f}" for y, v in fm["aeeh_beneficiaries"].items()))
    logger.info("🔎 France métropolitaine, foyers allocataires du RSA : " +
                ", ".join(f"{y} = {v:,.0f}" for y, v in fm["rsa_households"].items()))


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
            cur.execute("DELETE FROM caf_benefits_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY caf_benefits_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE caf_benefits_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des fichiers parquet de la Cnaf")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.dir)
    check(data, args.dir)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
