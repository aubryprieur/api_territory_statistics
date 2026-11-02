"""
Import de la précarité énergétique logement (Géodip, ONPE) dans energy_poverty_by_territory, millésime 2022.

Sources (data/housing/energy_poverty/) :
  - 2022/preca_niv_vie_{communes,EPCI,departements,regions}_2022.xlsx (Observatoire des territoires, ANCT) : part des
    ménages en précarité énergétique logement selon le niveau de vie (tx_preca_log_niv_vie, %), géographie 2026 ;
    France : 11,9 % (preca_niv_vie_France_2022.docx), France métropolitaine (pas d'estimation outre-mer).
  - 2023/nombre-de-menages-en-precarite-energetique-logement-{commune,epci,departement,region}.csv : nombre de
    ménages, date_mesure 2021-01-01 et 2022-01-01. Seul 2022-01-01 est retenu : il correspond au taux 2022 (même
    modèle) ; la série 2021-01-01 vient d'une version antérieure du modèle, non comparable.
    Arrondissements de Paris, Lyon, Marseille cumulés dans la commune ; France = somme des régions métropolitaines.

Usage :
    python scripts/import_energy_poverty_by_territory.py --dry-run
    python scripts/import_energy_poverty_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/housing/energy_poverty"
YEAR = 2022
FRANCE_RATE = 11.9  # preca_niv_vie_France_2022.docx
RATES = {"COM": "communes", "EPCI": "EPCI", "DEP": "departements", "REG": "regions"}
COUNTS = {"COM": ("commune", "geocode_commune"), "EPCI": ("epci", "geocode_epci"),
          "DEP": ("departement", "geocode_departement"), "REG": ("region", "geocode_region")}
PLM = {"751": "75056", "693": "69123", "132": "13055"}
COLUMNS = ["geo_level", "geo_code", "year", "energy_poverty_rate", "energy_poverty_households"]


def read_rates():
    parts = []
    for level, name in RATES.items():
        d = pd.read_excel(f"{DIR}/2022/preca_niv_vie_{name}_2022.xlsx", sheet_name="Data", skiprows=4,
                          dtype={"codgeo": str})
        d = d[["codgeo", "tx_preca_log_niv_vie"]].rename(columns={"codgeo": "geo_code",
                                                                   "tx_preca_log_niv_vie": "energy_poverty_rate"})
        d["geo_level"] = level
        parts.append(d)
        logger.info(f"📖 Taux {level} : {len(d):,} territoires, {d.energy_poverty_rate.notna().sum():,} valeurs")
    return pd.concat(parts, ignore_index=True)


def read_counts():
    parts = []
    for level, (name, col) in COUNTS.items():
        d = pd.read_csv(f"{DIR}/2023/nombre-de-menages-en-precarite-energetique-logement-{name}.csv",
                        dtype={col: str, "date_mesure": str})
        d = d[d.date_mesure == f"{YEAR}-01-01"]
        d = d.rename(columns={col: "geo_code", "valeur": "energy_poverty_households"})
        if level == "COM":  # arrondissements municipaux -> commune
            d["geo_code"] = d.geo_code.map(lambda x: PLM.get(x[:3], x) if x[:3] in PLM and x not in PLM.values() else x)
            d = d.groupby("geo_code", as_index=False).energy_poverty_households.sum()
        d["geo_level"] = level
        parts.append(d[["geo_level", "geo_code", "energy_poverty_households"]])
        logger.info(f"📖 Nombres {level} : {len(d):,} territoires, {d.energy_poverty_households.sum():,.0f} ménages")
    counts = pd.concat(parts, ignore_index=True)
    reg = counts[counts.geo_level == "REG"]
    metro = reg[~reg.geo_code.str.zfill(2).isin(["01", "02", "03", "04", "06"])]
    counts = pd.concat([counts, pd.DataFrame([{"geo_level": "FRANCE", "geo_code": "FM",
                                               "energy_poverty_households": metro.energy_poverty_households.sum()}])],
                       ignore_index=True)
    return counts


def build():
    rates = read_rates()
    rates = pd.concat([rates, pd.DataFrame([{"geo_level": "FRANCE", "geo_code": "FM",
                                             "energy_poverty_rate": FRANCE_RATE}])], ignore_index=True)
    data = rates.merge(read_counts(), on=["geo_level", "geo_code"], how="left")  # territoires de la géographie 2026
    data = data[data.energy_poverty_rate.notna() | data.energy_poverty_households.notna()]
    data["year"] = YEAR
    return data.reindex(columns=COLUMNS)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(['geo_level', 'geo_code']).sum()} ; "
                f"communes avec taux sans nombre : {(data.geo_level.eq('COM') & data.energy_poverty_households.isna() & data.energy_poverty_rate.notna()).sum()}")
    for level, code in (("COM", "59484"), ("COM", "91376"), ("COM", "75056"), ("COM", "13055"), ("EPCI", "200057859"),
                        ("DEP", "59"), ("REG", "32"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if not r.empty:
            r = r.iloc[0]
            implied = (r.energy_poverty_households / r.energy_poverty_rate * 100
                       if pd.notna(r.energy_poverty_households) and r.energy_poverty_rate else None)
            logger.info(f"🔎 {level} {code} : taux {r.energy_poverty_rate} %, {r.energy_poverty_households} ménages"
                        + (f" (soit ~{implied:,.0f} ménages au total)" if implied else ""))


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(conn, data):
    buf = io.StringIO()
    for row in data[COLUMNS].itertuples(index=False):
        buf.write("\t".join("\\N" if pd.isna(v) else str(v) for v in row) + "\n")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM energy_poverty_by_territory")
            cols = ", ".join(COLUMNS)
            cur.copy_expert(f"COPY energy_poverty_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
            cur.execute("SELECT count(*) FROM energy_poverty_by_territory")
            logger.info(f"🔎 Contrôle : {cur.fetchone()[0]:,} lignes en base")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche le contrôle sans écrire")
    args = parser.parse_args()
    data = build()
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        conn = _connect()
        try:
            write(conn, data)
            logger.info("🏁 Import terminé")
        finally:
            conn.close()
