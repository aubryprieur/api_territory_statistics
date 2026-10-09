"""
Import des crimes et délits enregistrés par la police et la gendarmerie (SSMSI, ministère de l'Intérieur,
bases communale, départementale et régionale 2016-2025, géographie 2026) dans delinquency_by_territory.

  COM, ARM : base communale (15 indicateurs). Les petits effectifs ne sont pas diffusés (est_diffuse = ndiff) :
             la base fournit alors une valeur imputée (complement_info_nombre) qui garantit que la somme des
             communes égale le département ; elle sert aux agrégats EPCI mais n'est pas affichée pour la commune.
  EPCI     : somme des communes (nombres diffusés + valeurs imputées), taux rapporté à la population (aux logements
             pour les cambriolages) des communes.
  DEP, REG : bases départementale et régionale (18 indicateurs, dont homicides et tentatives).
  FRANCE   : 'FM' = somme des départements de métropole.
Taux pour 1 000 habitants (pour 1 000 logements pour les cambriolages), comme publiés par le SSMSI.
Les faits sont comptés au lieu de commission, l'année de leur enregistrement.

Sources (data/delinquency/) :
  donnee-comm-data.gouv-parquet-2025-geographie2026-*.parquet, donnee-dep-data.gouv-2025-*.csv,
  donnee-reg-data.gouv-2025-*.csv, info-complements-data.gouv-2025-*.xlsx (communes -> EPCI)

Usage :
    python scripts/import_delinquency_by_territory.py --dry-run
    python scripts/import_delinquency_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/delinquency"
KEY = ["geo_level", "geo_code", "year"]
LONG = KEY + ["indicator", "count", "rate", "diffused", "population", "dwellings"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}

INDICATORS = {
    "Homicides": "homicide",
    "Tentatives d'homicide": "attempted_homicide",
    "Violences physiques intrafamiliales": "intrafamily_violence",
    "Violences physiques hors cadre familial": "other_physical_violence",
    "Violences sexuelles": "sexual_violence",
    "Vols avec armes": "armed_robbery",
    "Vols violents sans arme": "violent_theft",
    "Vols sans violence contre des personnes": "theft_without_violence",
    "Cambriolages de logement": "burglary",
    "Vols de véhicule": "vehicle_theft",
    "Vols dans les véhicules": "theft_from_vehicle",
    "Vols d'accessoires sur véhicules": "vehicle_accessory_theft",
    "Destructions et dégradations volontaires": "vandalism",
    "Usage de stupéfiants": "drug_use",
    "Usage de stupéfiants (AFD)": "drug_use_afd",
    "Usage de stupéfiants (hors AFD)": "drug_use_non_afd",
    "Trafic de stupéfiants": "drug_trafficking",
    "Escroqueries et fraudes aux moyens de paiement": "fraud",
}
PER_DWELLING = {"burglary"}
# Table large : une ligne par (territoire, année), trois colonnes par indicateur
COLUMNS = KEY + ["population", "dwellings"] + [
    f"{ind}_{m}" for ind in INDICATORS.values() for m in ("count", "rate", "diffused")]


def _file(d, pattern):
    files = sorted(glob.glob(os.path.join(d, pattern)))
    if not files:
        raise FileNotFoundError(f"{pattern} introuvable dans {d}")
    return files[-1]


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def _rate(count, population, dwellings, indicator):
    denom = np.where(indicator.isin(PER_DWELLING), dwellings, population)
    denom = pd.Series(denom, index=count.index).astype(float)
    return (count / denom * 1000).where(denom > 0).round(3)


def communes(d):
    c = pd.read_parquet(_file(d, "donnee-comm-*.parquet"))
    c["CODGEO_2026"] = c["CODGEO_2026"].astype(str).str.zfill(5)
    c["indicator"] = c["indicateur"].astype(str).map(INDICATORS)
    unknown = c.loc[c["indicator"].isna(), "indicateur"].astype(str).unique()
    if len(unknown):
        raise ValueError(f"Indicateurs inconnus : {list(unknown)}")
    c["diffused"] = c["est_diffuse"].astype(str) == "diff"
    c["count_est"] = c["nombre"].where(c["diffused"], c["complement_info_nombre"])
    return c


def build(d):
    c = communes(d)
    is_arm = c["CODGEO_2026"].str[:3].isin(ARM_PARENT) & ~c["CODGEO_2026"].isin(ARM_PARENT.values())
    com = pd.DataFrame({
        "geo_level": np.where(is_arm, "ARM", "COM"), "geo_code": c["CODGEO_2026"], "year": c["annee"].astype(int),
        "indicator": c["indicator"], "count": c["nombre"].where(c["diffused"]),
        "rate": c["taux_pour_mille"].where(c["diffused"]), "diffused": c["diffused"],
        "population": c["insee_pop"].astype(float), "dwellings": c["insee_log"].astype(float),
    })
    parts = [com]

    # Agrégats de communes : EPCI (et Paris, Lyon, Marseille si publiés par arrondissement)
    zon = pd.read_excel(_file(d, "info-complements-*.xlsx"), sheet_name="zonages supracommunaux", dtype=str)
    epci_of = zon.set_index("CODGEO")["EPCI"]
    c["epci"] = c["CODGEO_2026"].map(epci_of)
    c["is_arm"] = is_arm
    logger.info(f"   communes sans EPCI : {c.loc[c['epci'].isna(), 'CODGEO_2026'].nunique()}")

    def aggregate(frame, level, col):
        g = (frame.dropna(subset=[col])
             .groupby([col, "annee", "indicator"])
             .agg(count=("count_est", "sum"), population=("insee_pop", "sum"), dwellings=("insee_log", "sum"))
             .reset_index().rename(columns={col: "geo_code", "annee": "year"}))
        g["geo_level"], g["diffused"] = level, True
        g["count"] = g["count"].round(0)
        g["rate"] = _rate(g["count"], g["population"], g["dwellings"], g["indicator"])
        return g[LONG]

    # Paris, Lyon, Marseille figurent à la fois par commune et par arrondissement : agrégats sans les ARM
    parts.append(aggregate(c[(c["epci"].str.len() == 9) & ~is_arm], "EPCI", "epci"))

    # Départements et régions : bases publiées
    for level, pattern, code_col in (("DEP", "donnee-dep-*.csv", "Code_departement"),
                                     ("REG", "donnee-reg-*.csv", "Code_region")):
        t = pd.read_csv(_file(d, pattern), sep=";", dtype=str, encoding="utf-8-sig")
        t["indicator"] = t["indicateur"].map(INDICATORS)
        if t["indicator"].isna().any():
            raise ValueError(f"Indicateurs inconnus : {t.loc[t['indicator'].isna(), 'indicateur'].unique()}")
        parts.append(pd.DataFrame({
            "geo_level": level, "geo_code": t[code_col], "year": t["annee"].astype(int), "indicator": t["indicator"],
            "count": _num(t["nombre"]), "rate": _num(t["taux_pour_mille"]).round(3), "diffused": True,
            "population": _num(t["insee_pop"]), "dwellings": _num(t["insee_log"]),
        }))
        if level == "DEP":
            dep = parts[-1]
    metro = dep[~dep["geo_code"].str.startswith("97")]
    fm = metro.groupby(["year", "indicator"]).agg(count=("count", "sum"), population=("population", "sum"),
                                                  dwellings=("dwellings", "sum")).reset_index()
    fm["geo_level"], fm["geo_code"], fm["diffused"] = "FRANCE", "FM", True
    fm["rate"] = _rate(fm["count"], fm["population"], fm["dwellings"], fm["indicator"])
    parts.append(fm[LONG])
    long = pd.concat(parts, ignore_index=True)
    return wide(long), long, c


def wide(long):
    base = long.groupby(KEY).agg(population=("population", "max"), dwellings=("dwellings", "max"))
    values = long.pivot_table(index=KEY, columns="indicator", values=["count", "rate"], aggfunc="first")
    values.columns = [f"{ind}_{m}" for m, ind in values.columns]
    diffused = long.pivot_table(index=KEY, columns="indicator", values="diffused", aggfunc="first")
    diffused.columns = [f"{ind}_diffused" for ind in diffused.columns]
    data = base.join(values).join(diffused).reset_index()
    for col in COLUMNS:
        if col not in data:
            data[col] = np.nan
    return data[COLUMNS].sort_values(KEY).reset_index(drop=True)


def check(data, long, c):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    dup = long.duplicated(KEY + ["indicator"]).sum()
    logger.info(f"🔎 Doublons : {dup}")
    # La somme des communes (diffusées + imputées) doit égaler le département
    c["dep"] = c["CODGEO_2026"].str[:3].where(c["CODGEO_2026"].str.startswith("97"), c["CODGEO_2026"].str[:2])
    s = c[~c["is_arm"]].groupby(["dep", "annee", "indicator"])["count_est"].sum()
    dep = long[long.geo_level == "DEP"].set_index(["geo_code", "year", "indicator"])["count"]
    gap = (dep - s.reindex(dep.index)).abs().dropna()
    logger.info(f"🔎 Département - somme des communes : écart médian {gap.median():.1f}, max {gap.max():.0f}")
    y = data["year"].max()
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code) & (data.year == y)]
        if r.empty:
            continue
        r = r.iloc[0]
        txt = ", ".join(
            f"{k} {format(r[k + '_rate'], '.1f') if r[k + '_diffused'] else 'n.d.'}"
            for k in ("intrafamily_violence", "other_physical_violence", "burglary", "vandalism", "drug_use"))
        logger.info(f"🔎 {level} {code} {y} (‰) : {txt}")


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
    for col in [c for c in COLUMNS if c.endswith("_diffused")]:
        out[col] = out[col].map({True: "t", False: "f"})
    buf = io.StringIO()
    out[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM delinquency_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(
                f"COPY delinquency_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE delinquency_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des bases du SSMSI")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data, long, c = build(args.dir)
    check(data, long, c)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
