"""
Import des demandeurs d'emploi inscrits à France Travail (Dares, « Inscrits à France Travail — données communales,
trimestrielles, brutes ») dans job_seekers_by_territory.

Source : data/employment_seekers/dares_defm_communales-brutes.csv (format long : date, commune, catégorie ABC, sexe,
tranche d'âge, nombre). 4e trimestre de chaque année (moyenne trimestrielle), effectifs arrondis à 5 par la Dares,
géographie au 1er janvier 2024.

  COM   communes (Paris, Lyon, Marseille : ligne de la commune entière publiée par la Dares)
  ARM   arrondissements de Paris, Lyon, Marseille (exclus des sommes)
  EPCI  somme des communes (rattachement : data/geography/COG_au_01-01-2024.csv)
  DEP, REG  somme des communes
  FRANCE 'FM'  total « France métropolitaine » publié (y compris les demandeurs non localisés dans une commune)

Usage :
    python scripts/import_job_seekers_by_territory.py --dry-run
    python scripts/import_job_seekers_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE = "data/employment_seekers/dares_defm_communales-brutes.csv"
COG = "data/geography/COG_au_01-01-2024.csv"
KEY = ["geo_level", "geo_code", "year"]
MEASURES = ["abc", "abc_women", "abc_men", "abc_lt25", "abc_25_49", "abc_ge50"]
COLUMNS = KEY + MEASURES
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
# (sexe, tranche d'âge) -> colonne
CELLS = {("Total", "Total"): "abc", ("Femmes", "Total"): "abc_women", ("Hommes", "Total"): "abc_men",
         ("Total", "Moins de 25 ans"): "abc_lt25", ("Total", "De 25 à 49 ans"): "abc_25_49",
         ("Total", "50 ans et plus"): "abc_ge50"}


def read(path):
    logger.info(f"📖 Lecture de {path}")
    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig",
                     usecols=["Date", "Code région", "Code département", "Code commune", "Commune", "Catégorie",
                              "Sexe", "Tranche d'âge", "Nombre de demandeurs d'emploi"])
    df = df[df["Catégorie"] == "ABC"]
    df["year"] = df["Date"].str[:4].astype(int)
    df["value"] = pd.to_numeric(df["Nombre de demandeurs d'emploi"].str.replace(" ", ""), errors="coerce")
    df["measure"] = [CELLS.get(k) for k in zip(df["Sexe"], df["Tranche d'âge"])]
    df = df[df["measure"].notna()]
    logger.info(f"   {len(df):,} lignes ABC, années {sorted(df['year'].unique())}")
    return df


def wide(df, index):
    return (df.pivot_table(index=index, columns="measure", values="value", aggfunc="sum")
            .reset_index().reindex(columns=index + MEASURES))


def build(df):
    communes = df[df["Code commune"].str.match(r"^[0-9][0-9AB][0-9]{3}$", na=False)].copy()
    communes["geo_code"] = communes["Code commune"]
    com = wide(communes, ["geo_code", "Code département", "Code région", "year"])
    com_arm = com["geo_code"].str[:3].isin(ARM_PARENT) & ~com["geo_code"].isin(ARM_PARENT.values())
    parts = []

    c = com[~com_arm].assign(geo_level="COM")
    parts.append(c)
    parts.append(com[com_arm].assign(geo_level="ARM"))

    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    epci = dict(zip(geo["CODGEO"], geo["EPCI"]))
    base = c.copy()  # communes entières, sans arrondissements
    base["EPCI"] = base["geo_code"].map(epci)
    unmatched = base[base["EPCI"].isna()]["geo_code"].unique()
    logger.info(f"   Communes sans EPCI dans le COG 2024 : {len(unmatched)} {list(unmatched[:10])}")
    for level, col in (("EPCI", "EPCI"), ("DEP", "Code département"), ("REG", "Code région")):
        b = base[base[col].notna() & (base[col].str.len() <= 9) & (base[col] != "ZZZZZZZZZ")]
        agg = b.groupby([col, "year"])[MEASURES].sum(min_count=1).reset_index().rename(columns={col: "geo_code"})
        parts.append(agg.assign(geo_level=level))

    fm = df[df["Commune"] == "Total France métropolitaine"]
    fm = wide(fm.assign(geo_code="FM"), ["geo_code", "year"]).assign(geo_level="FRANCE")
    parts.append(fm)
    data = pd.concat(parts, ignore_index=True)[COLUMNS]
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    last = data["year"].max()
    fm = data[(data.geo_level == "FRANCE") & (data.year == last)]["abc"].sum()
    dep = data[(data.geo_level == "DEP") & (data.year == last) & ~data.geo_code.str.startswith("97")]["abc"].sum()
    logger.info(f"🔎 {last} : France métropolitaine publiée {fm:,.0f} ; somme des départements métropolitains {dep:,.0f} "
                f"(écart = non localisés + arrondis)")
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if not r.empty:
            logger.info(f"🔎 {level} {code} : ABC " + ", ".join(f"{y} {v:,.0f}" for y, v in r["abc"].items()))
    bad = data[(data[["abc_women", "abc_men"]].sum(axis=1, min_count=1) - data["abc"]).abs() > 20]
    logger.info(f"🔎 Lignes où femmes + hommes s'écarte du total de plus de 20 : {len(bad)}")


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
    out = data.copy()
    out["year"] = out["year"].astype(int)
    buf = io.StringIO()
    out[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM job_seekers_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY job_seekers_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE job_seekers_by_territory")
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
