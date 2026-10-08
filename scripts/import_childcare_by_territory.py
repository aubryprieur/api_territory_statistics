"""
Import accueil du jeune enfant (CAF / Cnaf) dans childcare_by_territory, à toutes les échelles
(valeurs officielles publiées par la Cnaf, aucune agrégation côté API) :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FE' = France entière hors Mayotte)

Sources (data.caf.fr, « Accueil du jeune enfant », années 2017 à 2023) :
  - nbpla_pe_<niveau>[_hist].parquet  : nombre de places par mode d'accueil
  - txcouv_pe_<niveau>[_hist].parquet : taux de couverture (places pour 100 enfants de moins de 3 ans)
    niveaux : com (communes publiées par la Cnaf, environ 1 000), epci, dep, reg, nat
    Les fichiers « _hist » couvrent 2017-2022 ; les fichiers récents (2022-2023) priment pour 2022 (révisé).
  - TAUXCOUV2020.csv, TAUXCOUV2021.csv : taux de couverture global de toutes les communes
    (complète les communes absentes des fichiers détaillés)

Modes d'accueil : établissements d'accueil du jeune enfant (EAJE) financés par la prestation de service
unique (PSU) ou hors PSU (micro-crèches Paje...), préscolarisation (enfants de 2 ans scolarisés),
assistantes maternelles, garde à domicile.

Usage :
    python scripts/import_childcare_by_territory.py              # fichiers par défaut
    python scripts/import_childcare_by_territory.py --dry-run    # contrôles sans écrire en base
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

DIR = "data/childcare/caf"
LEGACY_DIR = "data/childcare/commune/alternative"
FRANCE_CODE = "FE"   # France entière hors Mayotte (périmètre de publication de la Cnaf)
KEY = ["geo_level", "geo_code", "year"]

LEVELS = {  # niveau de fichier -> (geo_level, colonne du code)
    "com": ("COM", "numcom"),
    "epci": ("EPCI", "numepci"),
    "dep": ("DEP", "numdep"),
    "reg": ("REG", "numregi"),
    "nat": ("FRANCE", "national"),
}
MODES = {  # suffixe CAF -> nom de colonne
    "psu_col": "eaje_psu",
    "hors_psu_col": "eaje_hors_psu",
    "eaje": "eaje",
    "prescol": "preschool",
    "am_ind": "childminder",
    "gad_ind": "home_care",
    "ind": "individual",
}
PLACE_COLUMNS = [f"places_{m}" for m in MODES.values()] + ["places_total"]
RATE_COLUMNS = [f"rate_{m}" for m in MODES.values()] + ["rate_global"]
COLUMNS = KEY + PLACE_COLUMNS + RATE_COLUMNS + ["source"]

# Arrondissements municipaux publiés par la Cnaf comme des communes
ARM_PREFIXES = ("751", "6938", "132")


def _code(level, values):
    v = values.astype(str).str.strip()
    if level == "COM":
        return v.str.zfill(5)
    if level == "DEP":
        return v.where(v.str.len() > 2, v.str.zfill(2))
    if level == "REG":
        return v.str.zfill(2)
    return v


def _read(kind, level_key, d):
    geo_level, code_col = LEVELS[level_key]
    frames = []
    for suffix, rank in [("_hist", 0), ("", 1)]:  # le fichier récent prime (2022 révisé)
        path = os.path.join(d, f"{kind}_pe_{level_key}{suffix}.parquet")
        if not os.path.exists(path):
            logger.warning(f"⚠️ fichier absent : {path}")
            continue
        df = pd.read_parquet(path)
        df["year"] = df["annee"].astype(str).str[:4].astype(int)
        df["_rank"] = rank
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    lvl = f"_{level_key}"
    if kind == "nbpla":
        rename = {f"pl_{k}{lvl}": f"places_{v}" for k, v in MODES.items()}
        rename[f"tot_offre{lvl}"] = "places_total"
    else:
        rename = {f"txcouv_{k}{lvl}": f"rate_{v}" for k, v in MODES.items()}
        rename[f"txcouv{lvl}"] = "rate_global"
    df = df.rename(columns=rename)
    if geo_level == "FRANCE":
        df["geo_code"] = FRANCE_CODE
    else:
        df["geo_code"] = _code(geo_level, df[code_col])
    df["geo_level"] = geo_level
    if geo_level == "COM":
        df.loc[df["geo_code"].str.startswith(ARM_PREFIXES) & (df["geo_code"] != "13200"), "geo_level"] = "ARM"
    # Codes techniques (« XX », « COM »...) : hors champ
    df = df[~df["geo_code"].str.contains("X|COM", regex=True)]
    df = df.sort_values("_rank").drop_duplicates(KEY, keep="last")
    return df[KEY + list(rename.values())]


def load(d=DIR, legacy=LEGACY_DIR):
    parts = []
    for level_key in LEVELS:
        places = _read("nbpla", level_key, d)
        rates = _read("txcouv", level_key, d)
        parts.append(places.merge(rates, on=KEY, how="outer"))
    data = pd.concat(parts, ignore_index=True)
    data["source"] = "cnaf_detail"

    # Taux global de toutes les communes (2020, 2021) pour celles que la Cnaf ne détaille pas
    extra = []
    for year in (2020, 2021):
        path = os.path.join(legacy, f"TAUXCOUV{year}.csv")
        if not os.path.exists(path):
            logger.warning(f"⚠️ fichier absent : {path}")
            continue
        csv = pd.read_csv(path, sep=";", dtype=str)
        rate = pd.to_numeric(csv["tauxcouv_com"].str.replace(",", "."), errors="coerce")
        extra.append(pd.DataFrame({"geo_level": "COM", "geo_code": csv["NUM_COM"].str.strip().str.zfill(5),
                                   "year": year, "rate_global": rate, "source": "cnaf_tauxcouv"}))
    if extra:
        extra = pd.concat(extra, ignore_index=True).dropna(subset=["rate_global"])
        extra.loc[extra["geo_code"].str.startswith(ARM_PREFIXES) & (extra["geo_code"] != "13200"), "geo_level"] = "ARM"
        known = data.set_index(KEY).index
        extra = extra[~extra.set_index(KEY).index.isin(known)]
        data = pd.concat([data, extra], ignore_index=True)
    for col in COLUMNS:
        if col not in data.columns:
            data[col] = float("nan")
    return data[COLUMNS].sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau et année :")
    for line in data.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    detail = data[data.source == "cnaf_detail"]
    gap = (detail["rate_eaje"] + detail["rate_preschool"] + detail["rate_individual"] - detail["rate_global"]).abs()
    logger.info(f"🔎 Taux : EAJE + préscolarisation + individuel - global, écart max = {gap.max():.2f} pt (arrondis)")
    gap = (detail["places_eaje"] + detail["places_preschool"] + detail["places_individual"]
           - detail["places_total"]).abs()
    logger.info(f"🔎 Places : EAJE + préscolarisation + individuel - total, écart max = {gap.max():.0f}")
    dep = detail[detail.geo_level == "DEP"].groupby("year")["places_total"].sum()
    nat = detail[detail.geo_level == "FRANCE"].set_index("year")["places_total"]
    logger.info("🔎 Places totales, somme des départements vs France entière : " +
                ", ".join(f"{y} : {dep.get(y, float('nan')):,.0f} / {v:,.0f}" for y, v in nat.items()))
    fe = detail[detail.geo_level == "FRANCE"].set_index("year")["rate_global"]
    logger.info("🔎 France entière hors Mayotte, taux de couverture global : " +
                ", ".join(f"{y} = {v} %" for y, v in fe.items()))


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
            cur.execute("DELETE FROM childcare_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            cur.copy_expert(
                f"COPY childcare_by_territory ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE childcare_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des fichiers parquet de la Cnaf")
    parser.add_argument("--legacy-dir", default=LEGACY_DIR, help="dossier des fichiers TAUXCOUV<année>.csv")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.dir, args.legacy_dir)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
