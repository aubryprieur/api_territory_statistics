"""
Import de la construction neuve de logements (SDES — Sitadel, « Données annuelles communales — Logements »,
diffusion septembre 2026) dans construction_by_territory.

Source : data/construction/Donnees-annuelles-communales-Logements.2026-09.csv (séparateur « ; », deuxième ligne =
noms courts ANNEE, COMM, TYPE_LGT, LOG_AUT, LOG_COM, SDP_AUT, SDP_COM). Une ligne par (année, commune, type :
Tous Logements, Individuel pur, Individuel groupe, Collectif, Residence). Logements autorisés 2013-2025, commencés
2013-2024 (2025 non encore publié : NULL).

Géographie : chaque année est codée dans la géographie communale de l'année. Les codes présents dans le COG 2024
alimentent COM et EPCI ; les codes disparus (communes fusionnées depuis) ne sont comptés que dans DEP, REG et FM.
Paris, Lyon, Marseille : la commune entière est publiée (75056, 69123, 13055) ; les arrondissements de Paris et
Lyon sont importés en ARM et exclus des sommes. FRANCE 'FM' = somme des départements métropolitains.

Usage :
    python scripts/import_construction_by_territory.py --dry-run
    python scripts/import_construction_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE = "data/construction/Donnees-annuelles-communales-Logements.2026-09.csv"
COG = "data/geography/COG_au_01-01-2024.csv"
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
METRO_REGIONS = ["11", "24", "27", "28", "32", "44", "52", "53", "75", "76", "84", "93", "94"]
TYPES = {"Tous Logements": "total", "Individuel pur": "ind_pure", "Individuel groupe": "ind_group",
         "Collectif": "collective", "Residence": "residence"}
MEASURES = [f"{k}_{t}" for k in ("authorised", "started") for t in TYPES.values()]
COLUMNS = KEY + MEASURES


def dep_of(code):
    return code[:3] if code.startswith("97") else code[:2]


def read(path):
    logger.info(f"📖 Lecture de {path}")
    df = pd.read_csv(path, sep=";", dtype=str, skiprows=[1], encoding="utf-8-sig")
    df.columns = ["year", "code", "type", "authorised", "started", "sdp_authorised", "sdp_started"]
    df["year"] = df["year"].astype(int)
    df["code"] = df["code"].str.strip()
    df["type"] = df["type"].map(TYPES)
    unknown = df["type"].isna().sum()
    if unknown:
        logger.warning(f"   {unknown} lignes de type inconnu ignorées")
    df = df[df["type"].notna()]
    for c in ("authorised", "started"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    w = df.pivot_table(index=["code", "year"], columns="type", values=["authorised", "started"], aggfunc="sum",
                       dropna=False)
    w.columns = [f"{m}_{t}" for m, t in w.columns]
    w = w.reset_index().reindex(columns=["code", "year"] + MEASURES)
    # commencés non publiés pour la dernière année : NULL plutôt que 0
    for year in sorted(df["year"].unique()):
        if df.loc[df["year"] == year, "started"].notna().sum() == 0:
            w.loc[w["year"] == year, [m for m in MEASURES if m.startswith("started")]] = None
            logger.info(f"   {year} : logements commencés non publiés")
    logger.info(f"   {w['code'].nunique():,} codes communes, années {sorted(w['year'].unique())}")
    return w


def build(w):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    geo["DEP"] = geo["DEP"].where(geo["DEP"].str.len() > 1, geo["DEP"].str.zfill(2))
    known = set(geo["CODGEO"])
    epci = dict(zip(geo["CODGEO"], geo["EPCI"]))
    reg = dict(zip(geo["DEP"], geo["REG"]))

    is_arm = w["code"].str[:3].isin(ARM_PARENT) & ~w["code"].isin(ARM_PARENT.values())
    arm = w[is_arm]
    com = w[~is_arm].copy()
    com["dep"] = com["code"].map(dep_of)
    old = com[~com["code"].isin(known)]
    logger.info(f"   Codes absents du COG 2024 : {old['code'].nunique():,} ; logements commencés 2013-2024 "
                f"{old['started_total'].sum():,.0f} (comptés dans DEP / REG / FM seulement)")

    parts = []
    c = com[com["code"].isin(known)]
    parts.append(c.rename(columns={"code": "geo_code"})[["geo_code", "year"] + MEASURES].assign(geo_level="COM"))
    parts.append(arm.rename(columns={"code": "geo_code"})[["geo_code", "year"] + MEASURES].assign(geo_level="ARM"))
    e = c.assign(epci=c["code"].map(epci))
    e = e[e["epci"].notna() & (e["epci"] != "ZZZZZZZZZ")]
    parts.append(e.groupby(["epci", "year"])[MEASURES].sum(min_count=1).reset_index()
                 .rename(columns={"epci": "geo_code"}).assign(geo_level="EPCI"))
    d = com[com["dep"].isin(reg)]
    dep = d.groupby(["dep", "year"])[MEASURES].sum(min_count=1).reset_index()
    parts.append(dep.rename(columns={"dep": "geo_code"}).assign(geo_level="DEP"))
    r = dep.assign(reg=dep["dep"].map(reg))
    parts.append(r.groupby(["reg", "year"])[MEASURES].sum(min_count=1).reset_index()
                 .rename(columns={"reg": "geo_code"}).assign(geo_level="REG"))
    fm = r[r["reg"].isin(METRO_REGIONS)].groupby("year")[MEASURES].sum(min_count=1).reset_index()
    parts.append(fm.assign(geo_code="FM", geo_level="FRANCE"))
    data = pd.concat(parts, ignore_index=True)[COLUMNS]
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    parts = [m for m in MEASURES if not m.endswith("total")]
    for k in ("authorised", "started"):
        gap = (data[[m for m in parts if m.startswith(k)]].sum(axis=1, min_count=1) - data[f"{k}_total"]).abs().max()
        logger.info(f"🔎 {k} : écart maximal somme des types / total = {gap}")
    for level, code in (("COM", "59484"), ("COM", "75056"), ("EPCI", "245901160"), ("DEP", "59"), ("REG", "32"),
                        ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if r.empty:
            logger.info(f"🔎 {level} {code} : absent")
            continue
        logger.info(f"🔎 {level} {code} : commencés " + ", ".join(
            f"{y} {v:,.0f}" for y, v in r["started_total"].dropna().tail(5).items()) + " ; autorisés " + ", ".join(
            f"{y} {v:,.0f}" for y, v in r["authorised_total"].tail(3).items()))


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
            cur.execute("DELETE FROM construction_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY construction_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE construction_by_territory")
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
