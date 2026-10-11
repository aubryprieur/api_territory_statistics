"""
Import du répertoire des logements locatifs des bailleurs sociaux (RPLS au 1er janvier 2025, SDES) dans
social_housing_by_territory.

Source : data/social_housing/statistiques_sdes_resultats_rpls_2025_secret_donnees.xlsx (« Données nationales :
régions, départements, EPCI et communes »), onglets REGION, DEPARTEMENT, EPCI, COMMUNE ; ligne 6 = codes des variables.

Une ligne par (geo_level, geo_code, year) :
  - séries 2013 → 2025 (au 1er janvier) : parc social, logements mis en service, taux de vacance (totale et > 3 mois),
    taux de mobilité, loyer moyen au m²
  - 2025 seulement : structure du parc (densité pour 100 résidences principales, QPV, individuel, pièces, financement,
    âge, DPE énergie), sorties du parc
Niveaux :
  COM   communes (Paris, Lyon, Marseille : somme des arrondissements, taux pondérés)
  ARM   arrondissements
  EPCI  onglet EPCI (lignes par EPCI × département regroupées, taux pondérés)
  DEP, REG  onglets publiés ; FRANCE 'FM' : ligne « Total France métropolitaine »
Les communes absentes du fichier n'ont pas de logement social recensé.

Usage :
    python scripts/import_social_housing_by_territory.py --dry-run
    python scripts/import_social_housing_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE = "data/social_housing/statistiques_sdes_resultats_rpls_2025_secret_donnees.xlsx"
YEAR = 2025
YEARS = list(range(2013, YEAR + 1))
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}

# Séries : colonne de la table -> modèle de la colonne source ({s} = suffixe d'année, vide pour 2025)
SERIES = {"social_dwellings": "nb_ls{y}", "new_dwellings": "nv_mes{s}", "vacancy_rate": "tx_vac{s}",
          "vacancy_3m_rate": "tx_vac{s3}", "mobility_rate": "tx_mob{s}", "avg_rent_m2": "loymoy{s}"}
# Structure 2025 : colonne de la table -> colonne source (effectifs, sauf mention)
DETAIL = {
    "rented": "nb_loues", "vacant": "nb_vacants", "offered": "nb_loues_vacant", "density": "densite",
    "in_qpv": "nb_ls_en_qpv", "individual": "nb_ls_individuels", "collective": "nb_ls_collectifs",
    "rooms_1": "nb_ls_1piece", "rooms_2": "nb_ls_2piece", "rooms_3": "nb_ls_3piece", "rooms_4": "nb_ls_4piece",
    "rooms_5p": "nb_ls_5piece_plus", "fin_plai": "nb_ls_plai", "fin_plus_after_77": "nb_ls_plus_ap_77",
    "fin_plus_before_77": "nb_ls_plus_av_77", "fin_pls": "nb_ls_pls", "fin_pli": "nb_ls_pli",
    "avg_age": "age", "age_lt10": None, "age_ge60": "age_60_plus",
    "sold": None, "demolished": "nb_ls_demolition", "dpe_done": "nb_dpe_realise", "dpe_ab": None, "dpe_fg": None,
}
SERIES_COLUMNS = list(SERIES)
DETAIL_COLUMNS = list(DETAIL)
COLUMNS = KEY + SERIES_COLUMNS + DETAIL_COLUMNS
RATES = {"vacancy_rate": "offered", "vacancy_3m_rate": "offered", "mobility_rate": "offered",
         "avg_rent_m2": "rented", "avg_age": "social_dwellings"}  # taux -> pondération pour les regroupements


def read_sheet(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet, header=5, dtype=object)
    df = df[df.iloc[:, 0].notna()]
    for c in df.columns:
        if c not in ("REG", "LIBREG", "DEP", "LIBDEP", "EPCI_DEP", "LIBEPCI", "LIBCOM_DEP", "DEPCOM_ARM"):
            df[c] = pd.to_numeric(df[c], errors="coerce").replace([np.inf, -np.inf], np.nan)
    return df


def to_long(df, codes, level):
    """Une ligne par année (séries) + structure 2025 sur la ligne de 2025."""
    rows = []
    for y in YEARS:
        s = "" if y == YEAR else f"_{y}"
        cols = {}
        for col, pattern in SERIES.items():
            src = pattern.format(y="" if y == YEAR else y, s=s, s3=("3" if y == YEAR else f"_3_{y}"))
            cols[col] = df[src] if src in df else np.nan
        part = pd.DataFrame(cols)
        part["geo_code"], part["geo_level"], part["year"] = codes.values, level, y
        if y == YEAR:
            for col, src in DETAIL.items():
                if src:
                    part[col] = df[src].values
            part["age_lt10"] = (df["age_inf_5"].fillna(0) + df["age_5_10"].fillna(0)).values
            part["sold"] = df[["nb_ls_vendu_occupant", "nb_ls_vendu_autre_bailleur", "nb_ls_autre_vente"]].sum(axis=1, min_count=1).values
            part["dpe_ab"] = df[["ener_A", "ener_B", "ener_A_new", "ener_B_new"]].sum(axis=1, min_count=1).values
            part["dpe_fg"] = df[["ener_F", "ener_G", "ener_F_new", "ener_G_new"]].sum(axis=1, min_count=1).values
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    return out.reindex(columns=COLUMNS)


def regroup(long, level):
    """Somme des effectifs, taux pondérés (EPCI sur plusieurs départements, Paris / Lyon / Marseille)."""
    long = long.copy()
    long["rp"] = long["social_dwellings"] / long["density"] * 100  # résidences principales (2025)
    w = {}
    for rate, weight in RATES.items():
        wc = long[weight] if weight in long else long["social_dwellings"]
        wc = wc.where(long["year"] == YEAR, long["social_dwellings"])  # avant 2025 : pondération par le parc
        long[f"_w_{rate}"] = wc.where(long[rate].notna())
        long[f"_x_{rate}"] = long[rate] * long[f"_w_{rate}"]
        w[rate] = (f"_x_{rate}", f"_w_{rate}")
    counts = [c for c in SERIES_COLUMNS + DETAIL_COLUMNS if c not in RATES and c != "density"] + ["rp"]
    agg = long.groupby(["geo_code", "year"])[counts + [v for pair in w.values() for v in pair]].sum(min_count=1).reset_index()
    for rate, (x, wt) in w.items():
        agg[rate] = agg[x] / agg[wt]
    agg["density"] = (agg["social_dwellings"] / agg["rp"] * 100).where(agg["year"] == YEAR)
    agg["geo_level"] = level
    return agg.reindex(columns=COLUMNS)


def build(path):
    logger.info(f"📖 Lecture de {path}")
    parts = []
    reg = read_sheet(path, "REGION")
    reg["REG"] = reg["REG"].astype(str).str.zfill(2)
    fm = reg[reg["REG"] == "992"]
    parts.append(to_long(fm, pd.Series(["FM"] * len(fm)), "FRANCE"))
    reg = reg[reg["REG"].str.len() == 2]
    parts.append(to_long(reg, reg["REG"], "REG"))

    dep = read_sheet(path, "DEPARTEMENT")
    dep["DEP"] = dep["DEP"].astype(str).str.zfill(2)
    dep = dep[dep["DEP"].str.len() <= 3]
    parts.append(to_long(dep, dep["DEP"], "DEP"))

    epci = read_sheet(path, "EPCI")
    epci["code"] = epci["EPCI_DEP"].astype(str).str[:9]
    epci = epci[epci["code"].str.match(r"^\d{9}$")]
    parts.append(regroup(to_long(epci, epci["code"], "EPCI"), "EPCI"))

    com = read_sheet(path, "COMMUNE")
    com["code"] = com["DEPCOM_ARM"].astype(str).str.zfill(5)
    is_arm = com["code"].str[:3].isin(ARM_PARENT) & ~com["code"].isin(ARM_PARENT.values())
    parts.append(to_long(com[~is_arm], com.loc[~is_arm, "code"], "COM"))
    arm = to_long(com[is_arm], com.loc[is_arm, "code"], "ARM")
    parts.append(arm)
    plm = arm.copy()
    plm["geo_code"] = plm["geo_code"].str[:3].map(ARM_PARENT)
    parts.append(regroup(plm, "COM"))

    data = pd.concat(parts, ignore_index=True)[COLUMNS]
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    last = data[data.year == YEAR]
    fm = last[last.geo_level == "FRANCE"]["social_dwellings"].sum()
    dep = last[(last.geo_level == "DEP") & ~last.geo_code.str.startswith("97")]["social_dwellings"].sum()
    com = last[(last.geo_level == "COM") & ~last.geo_code.str.startswith("97")]["social_dwellings"].sum()
    logger.info(f"🔎 Parc social 2025 : France métro {fm:,.0f} ; somme des départements métro {dep:,.0f} ; "
                f"somme des communes métro {com:,.0f}")
    for level, code in (("COM", "59484"), ("COM", "75056"), ("EPCI", "245901160"), ("DEP", "59"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if r.empty:
            logger.info(f"🔎 {level} {code} : absent")
            continue
        l = r.loc[YEAR]
        logger.info(f"🔎 {level} {code} : parc {r['social_dwellings'].get(2013, np.nan):,.0f} (2013) → {l.social_dwellings:,.0f} ; "
                    f"densité {l.density:.1f} ; vacance {l.vacancy_rate:.1f} % ; mobilité {l.mobility_rate:.1f} % ; "
                    f"loyer {l.avg_rent_m2:.2f} €/m² ; QPV {l.in_qpv:,.0f} ; PLAI {l.fin_plai:,.0f} ; DPE F-G {l.dpe_fg:,.0f}/{l.dpe_done:,.0f}")


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
    num = [c for c in COLUMNS if c not in KEY]
    out[num] = out[num].astype(float).round(4)
    buf = io.StringIO()
    out[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM social_housing_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY social_housing_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE social_housing_by_territory")
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

    data = build(args.source)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
