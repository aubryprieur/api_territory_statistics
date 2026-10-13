"""
Import des créations d'entreprises (Insee, SIDE — « Créations d'entreprises et d'établissements pour l'année N »,
fichiers détail crent) dans business_creations_by_territory.

Sources : data/business_creations/*crent*_csv/(crent_|FD_CRENT_)<année>.csv, 2019-2025 (séparateur « ; » ;
REG, DEP, ZE, AAV, UU, COM, APE, A64, A38, A21, A10, TAILLE, CJ1, CJ2, FREQ). Créations d'entreprises (unités
légales) localisées à la commune du siège, champ marchand non agricole, micro-entrepreneurs compris.

Mesures par année :
  created               créations d'entreprises
  created_individual    entreprises individuelles (CJ1 = P, micro-entrepreneurs compris)
  created_company       sociétés (CJ1 = M)
  created_employer      créations avec au moins un salarié (TAILLE ≠ 00)
  sector_*              par grand secteur (A10) : industry (BE), construction (FZ), trade (GI : commerce,
                        transports, hébergement-restauration), business_services (JZ, KZ, LZ, MN : information,
                        finance, immobilier, activités spécialisées et administratives), personal_services (OQ, RU :
                        enseignement, santé, action sociale, autres services aux personnes)
Géographie : communes de l'année ; codes du COG 2024 → COM, EPCI ; autres codes seulement dans DEP / REG / FM.
Paris, Lyon, Marseille : arrondissements (ARM) et commune entière (COM = somme). FRANCE 'FM' = somme des
départements métropolitains.

Usage :
    python scripts/import_business_creations_by_territory.py --dry-run
    python scripts/import_business_creations_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import re
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/business_creations"
COG = "data/geography/COG_au_01-01-2024.csv"
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
METRO_REGIONS = ["11", "24", "27", "28", "32", "44", "52", "53", "75", "76", "84", "93", "94"]
SECTORS = {"BE": "sector_industry", "FZ": "sector_construction", "GI": "sector_trade",
           "JZ": "sector_business_services", "KZ": "sector_business_services", "LZ": "sector_business_services",
           "MN": "sector_business_services", "OQ": "sector_personal_services", "RU": "sector_personal_services"}
SECTOR_COLS = ["sector_industry", "sector_construction", "sector_trade", "sector_business_services",
               "sector_personal_services"]
MEASURES = ["created", "created_individual", "created_company", "created_employer"] + SECTOR_COLS
COLUMNS = KEY + MEASURES


def read(d):
    parts = []
    for path in sorted(glob.glob(os.path.join(d, "*crent*", "*.csv"))):
        name = os.path.basename(path)
        m = re.match(r"^(?:crent_|FD_CRENT_)(\d{4})\.csv$", name, re.I)
        if not m:
            continue
        year = int(m.group(1))
        df = pd.read_csv(path, sep=";", dtype=str, usecols=["DEP", "COM", "A10", "TAILLE", "CJ1", "FREQ"])
        df["n"] = pd.to_numeric(df["FREQ"])
        df["year"] = year
        logger.info(f"📖 {name} : {df['n'].sum():,.0f} créations")
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    unknown = set(df["A10"].unique()) - set(SECTORS)
    if unknown:
        logger.warning(f"   secteurs A10 inconnus : {unknown}")
    df["created"] = df["n"]
    df["created_individual"] = df["n"].where(df["CJ1"] == "P", 0)
    df["created_company"] = df["n"].where(df["CJ1"] == "M", 0)
    df["created_employer"] = df["n"].where(df["TAILLE"] != "00", 0)
    for col in SECTOR_COLS:
        df[col] = 0
    for code, col in SECTORS.items():
        df.loc[df["A10"] == code, col] += df.loc[df["A10"] == code, "n"]
    return df.groupby(["COM", "DEP", "year"])[MEASURES].sum().reset_index()


def build(com):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    geo["DEP"] = geo["DEP"].where(geo["DEP"].str.len() > 1, geo["DEP"].str.zfill(2))
    known = set(geo["CODGEO"])
    epci = dict(zip(geo["CODGEO"], geo["EPCI"]))
    reg = dict(zip(geo["DEP"], geo["REG"]))

    is_arm = com["COM"].str[:3].isin(ARM_PARENT) & ~com["COM"].isin(ARM_PARENT.values())
    com = com.assign(commune=com["COM"].where(~is_arm, com["COM"].str[:3].map(ARM_PARENT)))
    old = com[~com["commune"].isin(known)]
    logger.info(f"   Codes absents du COG 2024 : {old['COM'].nunique():,} ; {old['created'].sum():,.0f} créations "
                f"2019-2025 (comptées dans DEP / REG / FM seulement)")

    parts = []
    c = com[com["commune"].isin(known)]
    cg = c.groupby(["commune", "year"])[MEASURES].sum().reset_index()
    parts.append(cg.rename(columns={"commune": "geo_code"}).assign(geo_level="COM"))
    parts.append(com[is_arm].rename(columns={"COM": "geo_code"})[["geo_code", "year"] + MEASURES].assign(geo_level="ARM"))
    e = cg.assign(epci=cg["commune"].map(epci))
    e = e[e["epci"].notna() & (e["epci"] != "ZZZZZZZZZ")]
    parts.append(e.groupby(["epci", "year"])[MEASURES].sum().reset_index()
                 .rename(columns={"epci": "geo_code"}).assign(geo_level="EPCI"))
    dep = com[com["DEP"].isin(reg)].groupby(["DEP", "year"])[MEASURES].sum().reset_index()
    parts.append(dep.rename(columns={"DEP": "geo_code"}).assign(geo_level="DEP"))
    r = dep.assign(reg=dep["DEP"].map(reg))
    parts.append(r.groupby(["reg", "year"])[MEASURES].sum().reset_index()
                 .rename(columns={"reg": "geo_code"}).assign(geo_level="REG"))
    fm = r[r["reg"].isin(METRO_REGIONS)].groupby("year")[MEASURES].sum().reset_index()
    parts.append(fm.assign(geo_code="FM", geo_level="FRANCE"))
    data = pd.concat(parts, ignore_index=True)[COLUMNS]
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    gap = (data[SECTOR_COLS].sum(axis=1) - data["created"]).abs().max()
    gap2 = (data["created_individual"] + data["created_company"] - data["created"]).abs().max()
    logger.info(f"🔎 Écarts maximaux secteurs / total : {gap} ; EI + sociétés / total : {gap2}")
    for level, code in (("COM", "59484"), ("COM", "75056"), ("EPCI", "245901160"), ("DEP", "59"), ("REG", "32"),
                        ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if r.empty:
            logger.info(f"🔎 {level} {code} : absent")
            continue
        last = r.iloc[-1]
        logger.info(f"🔎 {level} {code} : créations " + ", ".join(f"{y} {v:,.0f}" for y, v in r["created"].items())
                    + f" ; {r.index[-1]} : EI {last['created_individual'] / last['created'] * 100:.0f} %, "
                    f"avec salariés {last['created_employer'] / last['created'] * 100:.1f} %")


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
        out[m] = out[m].round().astype("Int64")
    buf = io.StringIO()
    out[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM business_creations_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY business_creations_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE business_creations_by_territory")
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

    data = build(read(args.dir))
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
