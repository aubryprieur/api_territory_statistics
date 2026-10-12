"""
Import des associations (RNA — Répertoire national des associations, ministère de l'Intérieur, export Waldec du
1er octobre 2026) dans associations_by_territory.

Source : data/associations/rna_waldec_20261001/*.csv (un fichier par département de gestion, séparateur « ; »,
UTF-8). Le fichier Waldec contient toutes les associations créées ou ayant fait une démarche (modification,
dissolution) depuis 2009. Le fichier « rna_import » (associations sans démarche depuis 2009, sans code commune, pour
un tiers sans objet social) n'est pas utilisé : il est surtout composé d'associations en sommeil.

Rattachement : commune du siège (adrs_codeinsee). Indicateurs :
  - year = 2026 (stock au 1er octobre 2026) : associations en activité (position A, sans date de dissolution),
    total et par grande catégorie (premier objet social déclaré, nomenclature des objets sociaux du JOAFE) ;
  - year = 2010 … 2025 : créations d'associations dans l'année (date de création, associations dissoutes
    ensuite comprises).
Alsace-Moselle (57, 67, 68) : les associations y sont inscrites au tribunal judiciaire (droit local) et absentes du
RNA ; aucune valeur n'est publiée pour ces départements, leurs communes et EPCI. La région Grand Est (44) et la
France métropolitaine (FM) sont calculées sans ces trois départements (le service fait de même pour la population).
Niveaux : COM (Paris, Lyon, Marseille = somme des arrondissements), ARM, EPCI (COG 2024), DEP (préfixe du code
commune, communes anciennes comprises), REG, FRANCE 'FM'.

Usage :
    python scripts/import_associations_by_territory.py --dry-run
    python scripts/import_associations_by_territory.py
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

SOURCE = "data/associations/rna_waldec_20261001"
COG = "data/geography/COG_au_01-01-2024.csv"
STOCK_YEAR = 2026
FIRST_CREATION_YEAR, LAST_CREATION_YEAR = 2010, 2025
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
LOCAL_LAW = ["57", "67", "68"]
METRO_REGIONS = ["11", "24", "27", "28", "32", "44", "52", "53", "75", "76", "84", "93", "94"]
# grandes catégories : préfixe (3 chiffres) du premier objet social
THEMES = {
    "theme_sport": ["011"],
    "theme_culture": ["006", "010"],                       # culture, pratiques artistiques ; patrimoine
    "theme_leisure": ["007", "009", "013", "034"],         # clubs de loisirs ; action socio-culturelle, comités des fêtes ; chasse, pêche ; tourisme
    "theme_social": ["017", "018", "019", "020", "021"],   # santé ; médico-social ; interventions sociales ; caritatif, humanitaire ; services familiaux, personnes âgées
    "theme_education": ["015", "016"],                     # éducation, formation ; recherche
    "theme_friendly": ["014", "038"],                      # amicales, entraide ; anciens combattants, armée
    "theme_civic": ["001", "002", "003", "004", "005", "032", "036"],  # politique ; réflexion ; droits ; justice ; information ; logement ; sécurité, protection civile
    "theme_environment": ["024"],                          # environnement, cadre de vie
    "theme_economy": ["022", "023", "030"],                # activités économiques ; intérêts économiques ; emploi, développement local
    "theme_religion": ["040"],                             # religieux, spirituel, philosophique
}
THEME_OF = {p: t for t, ps in THEMES.items() for p in ps}
MEASURES = ["active"] + list(THEMES) + ["theme_other", "created"]
COLUMNS = KEY + MEASURES


def dep_of(code):
    if code.startswith("97") or code.startswith("98"):
        return code[:3]
    return code[:2]


def read(d):
    files = sorted(glob.glob(os.path.join(d, "*.csv")))
    logger.info(f"📖 {len(files)} fichiers dans {d}")
    cols = ["id", "date_creat", "date_disso", "objet_social1", "adrs_codeinsee", "position"]
    df = pd.concat([pd.read_csv(f, sep=";", dtype=str, usecols=cols, encoding="utf-8-sig") for f in files],
                   ignore_index=True)
    df = df.drop_duplicates("id")
    df["code"] = df["adrs_codeinsee"].fillna("").str.strip()
    df = df[df["code"].str.match(r"^[0-9][0-9AB][0-9]{3}$")]
    logger.info(f"   {len(df):,} associations avec un code commune")
    return df


def by_commune(df):
    active = df[(df["position"] == "A") & (df["date_disso"].fillna("0001-01-01") == "0001-01-01")].copy()
    active["theme"] = active["objet_social1"].fillna("").str[:3].map(THEME_OF).fillna("theme_other")
    stock = pd.crosstab(active["code"], active["theme"]).reindex(columns=list(THEMES) + ["theme_other"], fill_value=0)
    stock["active"] = stock.sum(axis=1)
    stock = stock.reset_index().assign(year=STOCK_YEAR)
    logger.info(f"   {len(active):,} associations en activité")

    year = pd.to_numeric(df["date_creat"].str[:4], errors="coerce")
    created = df[(year >= FIRST_CREATION_YEAR) & (year <= LAST_CREATION_YEAR)].assign(year=year.astype("Int64"))
    created = created.groupby(["code", "year"]).size().rename("created").reset_index()
    created["year"] = created["year"].astype(int)
    out = pd.concat([stock, created], ignore_index=True)
    return out.rename(columns={"code": "geo_code"})


def build(df):
    com = by_commune(df)
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    geo["DEP"] = geo["DEP"].where(geo["DEP"].str.len() > 1, geo["DEP"].str.zfill(2))
    known = set(geo["CODGEO"])
    epci = dict(zip(geo["CODGEO"], geo["EPCI"]))
    reg = dict(zip(geo["DEP"], geo["REG"]))

    com["dep"] = com["geo_code"].map(dep_of)
    is_arm = com["geo_code"].str[:3].isin(ARM_PARENT) & ~com["geo_code"].isin(ARM_PARENT.values())
    com["commune"] = com["geo_code"].where(~is_arm, com["geo_code"].str[:3].map(ARM_PARENT))
    unknown = com[~com["commune"].isin(known)]
    n_unknown = unknown.loc[unknown["year"] == STOCK_YEAR, "active"].sum()
    logger.info(f"   Codes absents du COG 2024 (communes fusionnées, collectivités d'outre-mer) : "
                f"{unknown['geo_code'].nunique():,} codes, {n_unknown:,.0f} associations en activité "
                f"(comptées dans les départements de France, pas dans les communes)")
    base = com[~com["dep"].isin(LOCAL_LAW)]

    parts = []
    c = base[base["commune"].isin(known)]
    parts.append(c.groupby(["commune", "year"])[MEASURES].sum(min_count=1).reset_index()
                 .rename(columns={"commune": "geo_code"}).assign(geo_level="COM"))
    parts.append(base[is_arm.loc[base.index]][["geo_code", "year"] + MEASURES].assign(geo_level="ARM"))

    e = c.assign(epci=c["commune"].map(epci))
    local_law_epci = set(geo.loc[geo["DEP"].isin(LOCAL_LAW), "EPCI"])
    e = e[e["epci"].notna() & (e["epci"] != "ZZZZZZZZZ") & ~e["epci"].isin(local_law_epci)]
    parts.append(e.groupby(["epci", "year"])[MEASURES].sum(min_count=1).reset_index()
                 .rename(columns={"epci": "geo_code"}).assign(geo_level="EPCI"))

    d = base[base["dep"].isin(reg)]
    dep = d.groupby(["dep", "year"])[MEASURES].sum(min_count=1).reset_index()
    parts.append(dep.rename(columns={"dep": "geo_code"}).assign(geo_level="DEP"))
    r = dep.assign(reg=dep["dep"].map(reg))
    parts.append(r.groupby(["reg", "year"])[MEASURES].sum(min_count=1).reset_index()
                 .rename(columns={"reg": "geo_code"}).assign(geo_level="REG"))
    fm = r[r["reg"].isin(METRO_REGIONS)].groupby("year")[MEASURES].sum(min_count=1).reset_index()
    parts.append(fm.assign(geo_code="FM", geo_level="FRANCE"))

    data = pd.concat(parts, ignore_index=True)[COLUMNS]
    stock_cols = ["active"] + list(THEMES) + ["theme_other"]
    data.loc[data["year"] != STOCK_YEAR, stock_cols] = None
    data.loc[data["year"] == STOCK_YEAR, "created"] = None
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    s = data[data["year"] == STOCK_YEAR]
    themes = list(THEMES) + ["theme_other"]
    gap = (s[themes].sum(axis=1) - s["active"]).abs().max()
    logger.info(f"🔎 Écart maximal somme des catégories / total : {gap}")
    for level, code in (("COM", "59484"), ("COM", "75056"), ("EPCI", "245901160"), ("DEP", "59"), ("REG", "32"),
                        ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if r.empty:
            logger.info(f"🔎 {level} {code} : absent")
            continue
        st = r.loc[STOCK_YEAR]
        shares = ", ".join(f"{t[6:]} {st[t] / st['active'] * 100:.0f} %" for t in themes)
        cr = r["created"].dropna()
        logger.info(f"🔎 {level} {code} : {st['active']:,.0f} en activité ({shares}) ; créations "
                    f"{', '.join(f'{y} {v:,.0f}' for y, v in cr.tail(4).items())}")


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(data):
    out = data.copy()
    out["year"] = out["year"].astype(int)
    for m in MEASURES:
        out[m] = out[m].astype("Int64")
    buf = io.StringIO()
    out[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM associations_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY associations_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE associations_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = build(read(args.source))
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
