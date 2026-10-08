"""
Import du tissu économique local (INSEE, Flores — établissements actifs et postes salariés au 31 décembre)
dans economic_fabric_by_territory, années 2017 et 2021 :
    COM, ARM (fichier communal) ; EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine) par somme des communes.

Sources (data/economy/) : base-cc-flores-2017.csv, base-cc-flores-2021.csv (chiffres clés « Flores »).
  - établissements actifs et postes salariés par grand secteur : agriculture (AZ), industrie (BE),
    construction (FZ), commerce, transports et services marchands (GU) dont commerce (GZ),
    services non marchands — administration publique, enseignement, santé, action sociale (OQ)
  - par taille : sans salarié, 1-9, 10-19, 20-49, 50 salariés ou plus (postes : 50-99, 100 ou plus)
  - sphère présentielle (activités tournées vers les besoins des habitants) / productive, dont domaine public
  - particuliers employeurs d'assistants maternels et d'autres salariés à domicile
Rattachement des communes aux EPCI et régions : data/geography/COG_au_01-01-2024.csv. Les départements sont
déduits du code commune. Les communes absentes du COG 2024 (fusionnées depuis) ne comptent pas dans les EPCI.

Usage :
    python scripts/import_economic_fabric_by_territory.py --dry-run
    python scripts/import_economic_fabric_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/economy"
COG = "data/geography/COG_au_01-01-2024.csv"
YEARS = (2017, 2021)
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}

SECTORS = {"AZ": "agriculture", "BE": "industry", "FZ": "construction", "GU": "market_services", "GZ": "trade",
           "OQ": "non_market"}
# code Flores (sans le suffixe d'année) -> colonne
SOURCE = {"ETTOT": "ets_total", "ETPTOT": "posts_total"}
for code, name in SECTORS.items():
    SOURCE[f"ET{code}"] = f"ets_{name}"
    SOURCE[f"ETP{code}"] = f"posts_{name}"
SOURCE.update({
    "ETTEF0": "ets_size_0", "ETTEF1": "ets_size_1_9", "ETTEF10": "ets_size_10_19", "ETTEF20": "ets_size_20_49",
    "ETTEF50": "ets_size_50p",
    "ETPTEF1": "posts_size_1_9", "ETPTEF10": "posts_size_10_19", "ETPTEF20": "posts_size_20_49",
    "ETPTEF50": "posts_size_50_99", "ETPTEFCP": "posts_size_100p",
    "ETPRES": "ets_presential", "ETNPRES": "ets_productive", "ETPRESPUB": "ets_presential_public",
    "ETNPRESPUB": "ets_productive_public",
    "ETPPRES": "posts_presential", "ETPNPRES": "posts_productive", "ETPPRESPUB": "posts_presential_public",
    "ETPNPRESPUB": "posts_productive_public",
    "ETASSMAT": "childminder_employers", "ETAUTRES": "other_home_employers",
})
MEASURES = list(SOURCE.values())
COLUMNS = KEY + MEASURES


def _communes(d, year):
    path = os.path.join(d, f"base-cc-flores-{year}.csv")
    df = pd.read_csv(path, sep=";", dtype={"CODGEO": str})
    suffix = str(year)[2:]
    rename = {f"{code}{suffix}": col for code, col in SOURCE.items()}
    missing = [c for c in rename if c not in df.columns]
    if missing:
        raise ValueError(f"{path} : colonnes absentes {missing}")
    df = df[["CODGEO", *rename]].rename(columns=rename)
    df[MEASURES] = df[MEASURES].apply(pd.to_numeric, errors="coerce")
    df["geo_code"] = df["CODGEO"].str.strip().str.zfill(5)
    df["year"] = year
    is_arm = df["geo_code"].str[:3].isin(ARM_PARENT) & ~df["geo_code"].isin(ARM_PARENT.values())
    df["geo_level"] = "COM"
    df.loc[is_arm, "geo_level"] = "ARM"
    df["parent"] = df["geo_code"].where(~is_arm, df["geo_code"].str[:3].map(ARM_PARENT))
    df["dep"] = df["geo_code"].str[:3].where(df["geo_code"].str.startswith("97"), df["geo_code"].str[:2])
    return df


def load(d=DIR, cog=COG):
    geo = pd.read_csv(cog, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    geo["DEP"] = geo["DEP"].str.zfill(2)
    epci_of = geo.set_index("CODGEO")["EPCI"]
    reg_of_dep = geo.drop_duplicates("DEP").set_index("DEP")["REG"].str.zfill(2)
    parts = []
    for year in YEARS:
        com = _communes(d, year)
        parts.append(com[COLUMNS])
        com["epci"] = com["parent"].map(epci_of)
        unmapped = com["epci"].isna()
        logger.info(f"   {year} : {len(com)} communes, {unmapped.sum()} sans EPCI dans le COG 2024 "
                    f"({com.loc[unmapped, 'posts_total'].sum():,.0f} postes)")
        # Les arrondissements comptent dans les agrégats ; la commune parente (75056...) n'est pas dans le fichier
        for level, col in (("EPCI", "epci"), ("DEP", "dep")):
            agg = com.dropna(subset=[col]).groupby(col)[MEASURES].sum(min_count=1).reset_index()
            agg = agg.rename(columns={col: "geo_code"})
            agg["geo_level"], agg["year"] = level, year
            parts.append(agg[COLUMNS])
        com["reg"] = com["dep"].map(reg_of_dep)
        reg = com.dropna(subset=["reg"]).groupby("reg")[MEASURES].sum(min_count=1).reset_index()
        reg = reg.rename(columns={"reg": "geo_code"})
        reg["geo_level"], reg["year"] = "REG", year
        parts.append(reg[COLUMNS])
        metro = com[~com["dep"].str.startswith("97")]
        fm = metro[MEASURES].sum(min_count=1).to_frame().T
        fm["geo_level"], fm["geo_code"], fm["year"] = "FRANCE", "FM", year
        parts.append(fm[COLUMNS])
    data = pd.concat(parts, ignore_index=True)
    data["year"] = data["year"].astype(int)
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau et année :")
    for line in data.groupby(["geo_level", "year"]).size().unstack(fill_value=0).to_string().splitlines():
        logger.info("   " + line)
    sectors = [f"posts_{s}" for s in SECTORS.values() if s != "trade"]
    gap = (data[sectors].sum(axis=1) - data["posts_total"]).abs().max()
    logger.info(f"🔎 Postes : somme des secteurs - total, écart max = {gap:.0f}")
    gap = (data["posts_presential"] + data["posts_productive"] - data["posts_total"]).abs().max()
    logger.info(f"🔎 Postes : présentiel + productif - total, écart max = {gap:.0f}")
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("FRANCE", "FM")):
        rows = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if rows.empty:
            continue
        txt = ", ".join(
            f"{y} : {r.posts_total:,.0f} postes / {r.ets_total:,.0f} établissements, services non marchands "
            f"{r.posts_non_market / r.posts_total:.0%}, présentiel {r.posts_presential / r.posts_total:.0%}, "
            f"employeurs d'assistants maternels {r.childminder_employers:,.0f}"
            for y, r in rows.iterrows())
        logger.info(f"🔎 {level} {code} — {txt}")


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
    years = sorted(int(y) for y in data["year"].unique())
    buf = io.StringIO()
    data.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM economic_fabric_by_territory WHERE year = ANY(%s)", (years,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {years}")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(
                f"COPY economic_fabric_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE economic_fabric_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des fichiers base-cc-flores-<année>.csv")
    parser.add_argument("--cog", default=COG, help="fichier COG (communes, EPCI, départements, régions)")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.dir, args.cog)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
