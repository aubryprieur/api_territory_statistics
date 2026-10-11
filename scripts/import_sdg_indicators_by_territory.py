"""
Import d'indicateurs territoriaux de développement durable (INSEE / SDES, base « ODD », fichiers parquet par
niveau) dans sdg_indicators_by_territory : une sélection d'indicateurs utiles à l'analyse des besoins sociaux, répartis
ensuite dans les onglets du dashboard (Diplômes, Emploi, Logement, Équipements).

  COM, ARM (ODD_COM), EPCI (ODD_EPCI), DEP (ODD_DEP), REG (ODD_REG), FRANCE 'FM' (ODD_MET = France métropolitaine)

Sources (data/odd/) : ODD_COM.parquet, ODD_EPCI.parquet, ODD_DEP.parquet, ODD_REG.parquet, ODD_MET.parquet
(archive ODD_PARQUET.zip). Chaque ligne source : codgeo, no_indic, variable, sous_champ, A1982 ... A2025.

Usage :
    python scripts/import_sdg_indicators_by_territory.py --dry-run
    python scripts/import_sdg_indicators_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/odd"
FIRST_YEAR = 2006
KEY = ["geo_level", "geo_code", "year"]
LEVELS = {"COM": "ODD_COM", "EPCI": "ODD_EPCI", "DEP": "ODD_DEP", "REG": "ODD_REG", "FRANCE": "ODD_MET"}
ARM_PREFIXES = ("751", "6938", "132")
ARM_PARENTS = {"75056", "69123", "13055"}

# colonne -> (no_indic, variable, sous_champ)
SPECS = {
    "young_neet_rate": ("i052", "part_jeunes_non_inseres", ""),          # 18-24 ans ni en emploi ni en études (%)
    "young_no_diploma_rate": ("i024", "part_20_24_sortis_nondip", ""),   # 20-24 ans sortis sans diplôme (%)
    "long_term_unemployed_share": ("i048", "part_chomeurs_ld", ""),      # chômeurs depuis plus d'un an (%)
    "employment_gap_women_men": ("i027", "ecart_tx_emp_f_h", "total"),   # écart de taux d'emploi F - H (points)
    "employment_gap_women_men_25_54": ("i027", "ecart_tx_emp_f_h", "25_54"),
    "ess_jobs_share": ("i050a", "part_emp_ess", ""),                     # emplois de l'économie sociale et solidaire (%)
    "gp_accessibility": ("i113", "apl_medgen_moins65", ""),             # APL médecins généralistes (consultations/an/hab.)
    "commute_minutes": ("i061a", "med_dist_min_hp", "act"),             # durée médiane domicile-travail (min)
    "commute_km": ("i061b", "med_dist_km", "act"),                      # distance médiane domicile-travail (km)
    "commute_car_share": ("i062", "part_depl_dom_trav", "voiture"),     # mode principal de transport (%)
    "commute_public_transport_share": ("i062", "part_depl_dom_trav", "tec"),
    "commute_walk_share": ("i062", "part_depl_dom_trav", "pied"),
    "commute_bike_share": ("i062", "part_depl_dom_trav", "velo"),
    "commute_two_wheels_share": ("i062", "part_depl_dom_trav", "deux_roues"),
    "commute_no_transport_share": ("i062", "part_depl_dom_trav", "sans_transp"),
    "social_housing_share": ("i079a", "part_pls", ""),                  # logements sociaux / résidences principales (%)
    "vacant_housing_share": ("i085", "part_log", "vac"),                # logements vacants (%)
    "presidential_turnout": ("i110", "taux_participation", ""),         # participation 1er tour présidentielle (%)
}
MEASURES = list(SPECS)
COLUMNS = KEY + MEASURES


def load_level(d, level, name):
    path = os.path.join(d, f"{name}.parquet")
    indics = sorted({s[0] for s in SPECS.values()})
    df = pd.read_parquet(path, filters=[("no_indic", "in", indics)])
    df["sous_champ"] = df["sous_champ"].fillna("").astype(str)
    years = [c for c in df.columns if c.startswith("A") and c[1:].isdigit() and int(c[1:]) >= FIRST_YEAR]
    parts = []
    for col, (indic, var, sub) in SPECS.items():
        sel = df[(df["no_indic"] == indic) & (df["variable"] == var) & (df["sous_champ"] == sub)]
        if sel.empty:
            logger.warning(f"   {level} : {col} absent ({indic} {var} {sub})")
            continue
        long = sel.melt(id_vars=["codgeo"], value_vars=years, var_name="year", value_name="value").dropna(subset=["value"])
        long["year"] = long["year"].str[1:].astype(int)
        long["measure"] = col
        parts.append(long)
    long = pd.concat(parts, ignore_index=True).drop_duplicates(["codgeo", "year", "measure"])
    wide = long.pivot_table(index=["codgeo", "year"], columns="measure", values="value", aggfunc="first").reset_index()
    wide = wide.rename(columns={"codgeo": "geo_code"})
    wide["geo_code"] = wide["geo_code"].astype(str)
    if level == "FRANCE":
        wide["geo_code"] = "FM"
    wide["geo_level"] = level
    if level == "COM":
        is_arm = wide["geo_code"].str.startswith(ARM_PREFIXES) & ~wide["geo_code"].isin(ARM_PARENTS)
        wide.loc[is_arm, "geo_level"] = "ARM"
    for c in MEASURES:
        if c not in wide:
            wide[c] = float("nan")
    return wide[COLUMNS]


def build(d=DIR):
    data = pd.concat([load_level(d, level, name) for level, name in LEVELS.items()], ignore_index=True)
    data[MEASURES] = data[MEASURES].round(3)
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    for col in MEASURES:
        years = sorted(data.loc[data[col].notna(), "year"].unique())
        logger.info(f"   {col} : {data[col].notna().sum():,} valeurs, années {years[:3]}...{years[-2:]}")
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if r.empty:
            continue
        last = {c: r.dropna(subset=[c]).sort_values("year").iloc[-1][[c, "year"]].tolist()
                for c in ("young_neet_rate", "long_term_unemployed_share", "gp_accessibility", "social_housing_share",
                          "commute_minutes", "presidential_turnout") if r[c].notna().any()}
        logger.info(f"🔎 {level} {code} : " + ", ".join(f"{k} {v:.1f} ({int(y)})" for k, (v, y) in last.items()))


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
            cur.execute("DELETE FROM sdg_indicators_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(
                f"COPY sdg_indicators_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE sdg_indicators_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des fichiers ODD_*.parquet")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = build(args.dir)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
