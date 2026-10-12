"""
Import des licences sportives (INJEP — MEOS, recensement des licences et clubs sportifs 2023, diffusion Observatoire
des territoires — ANCT) dans sports_by_territory.

Sources : data/sports/licsport*(communes|epci|departement(s)|regions).xlsx, onglet « Data » (ligne 5 = en-têtes :
codgeo, libgeo, an, indicateur). Neuf indicateurs :
  licence_rate          licenciés pour 100 habitants
  licence_rate_0_14     licenciés de 0-14 ans pour 100 habitants de 0-14 ans
  licence_rate_15_29    licenciés de 15-29 ans pour 100 habitants de 15-29 ans
  licence_rate_30_59    licenciés de 30-59 ans pour 100 habitants de 30-59 ans
  licence_rate_60p      licenciés de 60 ans ou plus pour 100 habitants de 60 ans ou plus
  girls_share_0_14      part des filles parmi les licenciés de 0-14 ans
  women_share_15_29     part des femmes parmi les licenciés de 15-29 ans
  women_share_30_59     part des femmes parmi les licenciés de 30-59 ans
  women_share_60p       part des femmes parmi les licenciés de 60 ans ou plus
Niveaux : COM, ARM, EPCI, DEP, REG publiés (2023 ; les séries départementales et régionales 2016-2022 ne sont pas
importées, faute de série communale) ; FRANCE 'FM' : valeurs nationales publiées par l'Observatoire des territoires
(NATIONAL) ; la moyenne des 13 régions métropolitaines pondérée par la population (base requise) est affichée pour
contrôle.

Usage :
    python scripts/import_sports_by_territory.py --dry-run
    python scripts/import_sports_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/sports"
YEAR = 2023
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
METRO_REGIONS = ["11", "24", "27", "28", "32", "44", "52", "53", "75", "76", "84", "93", "94"]
INDICATORS = {"p_licsport": "licence_rate", "p_licsport014": "licence_rate_0_14", "p_licsport1529": "licence_rate_15_29",
              "p_licsport3059": "licence_rate_30_59", "p_licsport60": "licence_rate_60p",
              "p_licsport014_f": "girls_share_0_14", "p_licsport1529_f": "women_share_15_29",
              "p_licsport3059_f": "women_share_30_59", "p_licsport60_f": "women_share_60p"}
MEASURES = list(INDICATORS.values())
COLUMNS = KEY + MEASURES
# pondération de la moyenne France métropolitaine (tranches de 5 ans de la pyramide 2023)
WEIGHTS = {"licence_rate": "pop", "licence_rate_0_14": "pop_0_14", "licence_rate_60p": "pop_ge60", "licence_rate_15_29": "pop_15_29", "licence_rate_30_59": "pop_30_59",
           "girls_share_0_14": "pop_0_14", "women_share_15_29": "pop_15_29", "women_share_30_59": "pop_30_59",
           "women_share_60p": "pop_ge60"}
LEVELS = {"communes": "COM", "epci": "EPCI", "departement": "DEP", "region": "REG"}


def level_of(path):
    name = os.path.basename(path).lower()
    for key, level in LEVELS.items():
        if f"({key}" in name:
            return level
    raise ValueError(f"niveau inconnu : {path}")


def read(d):
    parts = {}
    for path in sorted(glob.glob(os.path.join(d, "licsport*.xlsx"))):
        level = level_of(path)
        df = pd.read_excel(path, sheet_name="Data", header=4, dtype={"codgeo": str})
        col = df.columns[3]
        if col not in INDICATORS:
            logger.warning(f"   indicateur inconnu {col} ({path})")
            continue
        df = df[pd.to_numeric(df["an"], errors="coerce") == YEAR]
        s = df.set_index("codgeo")[col].rename(INDICATORS[col])
        parts.setdefault(level, []).append(s)
    out = []
    for level, series in parts.items():
        w = pd.concat(series, axis=1).reset_index().rename(columns={"codgeo": "geo_code"})
        w["geo_code"] = w["geo_code"].astype(str).str.strip()
        w["geo_level"] = level
        if level == "COM":
            w["geo_code"] = w["geo_code"].str.zfill(5)
            arm = w["geo_code"].str[:3].isin(ARM_PARENT) & ~w["geo_code"].isin(ARM_PARENT.values())
            w.loc[arm, "geo_level"] = "ARM"
        elif level in ("DEP", "REG"):
            w["geo_code"] = w["geo_code"].str.zfill(2)
        out.append(w)
    data = pd.concat(out, ignore_index=True)
    data["year"] = YEAR
    return data.reindex(columns=COLUMNS)


def regional_populations():
    try:
        conn = _connect()
    except Exception as e:  # pas de base (dry-run hors du Mac)
        logger.warning(f"   Base indisponible ({e.__class__.__name__}) : France métropolitaine non calculée")
        return None
    groups = {"pop_0_14": ["0_4", "5_9", "10_14"], "pop_15_29": ["15_19", "20_24", "25_29"],
              "pop_30_59": ["30_34", "35_39", "40_44", "45_49", "50_54", "55_59"]}
    sel = ["geo_code", "pop", "pop_ge65"] + [f"pyr_{s}_{g}" for g in ["60_64"] + sum(groups.values(), []) for s in ("men", "women")]
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(sel)} FROM population_by_territory WHERE geo_level = 'REG' AND year = {YEAR}")
            df = pd.DataFrame(cur.fetchall(), columns=sel)
    finally:
        conn.close()
    for c in sel[1:]:
        df[c] = df[c].astype(float)
    for k, gs in groups.items():
        df[k] = sum(df[f"pyr_{s}_{g}"] for g in gs for s in ("men", "women"))
    df["pop_ge60"] = df["pop_ge65"] + df["pyr_men_60_64"] + df["pyr_women_60_64"]
    return df[["geo_code", "pop", "pop_0_14", "pop_15_29", "pop_30_59", "pop_ge60"]]


# Valeurs nationales publiées par l'Observatoire des territoires (légende des cartes, non disponibles en tableur ;
# relevées dans data/sports/Licenciés sportifs au niveau national.docx). Elles remplacent la moyenne pondérée des
# régions (calculée et affichée pour contrôle).
NATIONAL = {"licence_rate": 23.7, "licence_rate_0_14": 63.5, "licence_rate_60p": 9.8, "licence_rate_15_29": 27.1, "licence_rate_30_59": 14.4, "girls_share_0_14": 41.4,
            "women_share_15_29": 35.3, "women_share_30_59": 33.7, "women_share_60p": 44.4}


def add_france(data, pops):
    if pops is None:
        fm = {"geo_level": "FRANCE", "geo_code": "FM", "year": YEAR, **NATIONAL}
        return pd.concat([data, pd.DataFrame([fm])], ignore_index=True)[COLUMNS]
    reg = data[(data.geo_level == "REG") & data.geo_code.isin(METRO_REGIONS)].merge(pops, on="geo_code")
    fm = {"geo_level": "FRANCE", "geo_code": "FM", "year": YEAR}
    for m in MEASURES:
        w = WEIGHTS[m]
        ok = reg[m].notna() & reg[w].notna()
        fm[m] = round((reg.loc[ok, m] * reg.loc[ok, w]).sum() / reg.loc[ok, w].sum(), 1)
    logger.info("   France : moyenne pondérée des régions " + ", ".join(f"{m} {fm[m]}" for m in MEASURES))
    fm.update(NATIONAL)
    return pd.concat([data, pd.DataFrame([fm])], ignore_index=True)[COLUMNS]


def check(data):
    logger.info(f"🔎 Lignes par niveau : {data.groupby('geo_level').size().to_dict()} ; doublons {data.duplicated(KEY).sum()}")
    for level, code in (("COM", "59484"), ("COM", "75056"), ("ARM", "75101"), ("EPCI", "245901160"), ("DEP", "59"),
                        ("REG", "32"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if r.empty:
            logger.info(f"🔎 {level} {code} : absent")
            continue
        r = r.iloc[0]
        logger.info(f"🔎 {level} {code} : {r.licence_rate} licences pour 100 hab. ; 15-29 ans {r.licence_rate_15_29} ; "
                    f"30-59 ans {r.licence_rate_30_59} ; filles 0-14 ans {r.girls_share_0_14} % ; femmes 60 ans ou + {r.women_share_60p} %")


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(data):
    buf = io.StringIO()
    data[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sports_by_territory")
            cols = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY sports_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ sports_by_territory : {cur.rowcount:,} lignes importées")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = add_france(read(args.dir), regional_populations())
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
