"""
Import de la Base permanente des équipements (BPE 2025, INSEE) :

  equipment_types          libellé, domaine et sous-domaine de chaque type d'équipement (TYPEQU)
  equipment_by_territory   nombre d'équipements par type et par territoire, dont situés en quartier prioritaire
                           (QPV 2024) : COM, ARM (+ COM Paris, Lyon, Marseille = somme des arrondissements), EPCI,
                           DEP, REG, FRANCE ('FM' = France métropolitaine)
  equipment_nearest        pour chaque commune qui n'a pas un service clé (app/equipment_catalog.py), distance à vol
                           d'oiseau au plus proche et commune où il se trouve. Point de référence de la commune :
                           la mairie (à défaut, le centre des équipements de la commune). Calcul par système de
                           coordonnées (Lambert 93 en métropole, projections locales outre-mer).

Sources (data/equipment/) : BPE25.parquet (ou bpe25_slim.parquet, colonnes utiles seulement),
BPE25_anonymisee_varmod.csv (libellés).

Usage :
    python scripts/import_equipment_by_territory.py --dry-run
    python scripts/import_equipment_by_territory.py
Nécessite scipy (recherche du plus proche voisin) : pip install scipy
"""
import argparse
import io
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.equipment_catalog import SERVICES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/equipment"
YEAR = 2025
COLUMNS = ["DEPCOM", "DEP", "REG", "EPCI", "LIBCOM", "TYPEQU", "QP2024", "LAMBERT_X", "LAMBERT_Y", "EPSG"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
COUNT_COLUMNS = ["geo_level", "geo_code", "year", "typequ", "count", "count_qpv"]
TYPE_COLUMNS = ["typequ", "label", "domain", "domain_label", "subdomain", "subdomain_label"]
NEAREST_COLUMNS = ["geo_code", "year", "service", "distance_km", "nearest_code", "nearest_name"]


def read(d):
    for name in ("bpe25_slim.parquet", "BPE25.parquet"):
        path = os.path.join(d, name)
        if os.path.exists(path):
            logger.info(f"📖 Lecture de {path}")
            df = pd.read_parquet(path, columns=COLUMNS)
            break
    else:
        raise FileNotFoundError(f"BPE introuvable dans {d}")
    for c in ["DEPCOM", "DEP", "REG", "EPCI", "LIBCOM", "TYPEQU", "QP2024", "EPSG"]:
        df[c] = df[c].astype(str)
    df["qpv"] = df["QP2024"].str.startswith("QN").astype(int)
    return df


def types(d):
    vm = pd.read_csv(os.path.join(d, "BPE25_anonymisee_varmod.csv"), sep=";", dtype=str, header=None,
                     names=["var", "var_label", "code", "label", "type", "len", "x", "y"])
    lab = lambda v: vm[vm["var"] == v].set_index("code")["label"]  # noqa: E731
    t = lab("TYPEQU").rename("label").reset_index().rename(columns={"code": "typequ"})
    t["label"] = t["label"].str.capitalize()
    t["domain"], t["subdomain"] = t["typequ"].str[0], t["typequ"].str[:2]
    t["domain_label"] = t["domain"].map(lab("DOM"))
    t["subdomain_label"] = t["subdomain"].map(lab("SDOM"))
    return t[TYPE_COLUMNS]


def counts(df):
    is_arm = df["DEPCOM"].str[:3].isin(ARM_PARENT) & ~df["DEPCOM"].isin(ARM_PARENT.values())
    df = df.assign(level_com=np.where(is_arm, "ARM", "COM"),
                   parent=df["DEPCOM"].where(~is_arm, df["DEPCOM"].str[:3].map(ARM_PARENT)))
    parts = []

    def agg(frame, level, col):
        g = frame.groupby([col, "TYPEQU"]).agg(count=("qpv", "size"), count_qpv=("qpv", "sum")).reset_index()
        g = g.rename(columns={col: "geo_code", "TYPEQU": "typequ"})
        g["geo_level"], g["year"] = level, YEAR
        return g[COUNT_COLUMNS]

    parts.append(agg(df[~is_arm], "COM", "DEPCOM"))
    parts.append(agg(df[is_arm], "ARM", "DEPCOM"))
    parts.append(agg(df[is_arm], "COM", "parent"))  # Paris, Lyon, Marseille
    parts.append(agg(df[df["EPCI"].str.len() == 9], "EPCI", "EPCI"))
    parts.append(agg(df, "DEP", "DEP"))
    parts.append(agg(df, "REG", "REG"))
    fm = df[~df["DEP"].str.startswith("97")].assign(fm="FM")
    parts.append(agg(fm, "FRANCE", "fm"))
    return pd.concat(parts, ignore_index=True)


def reference_points(df):
    """Point de référence de chaque commune (ARM comprises) : mairie, sinon centre de ses équipements."""
    xy = df.dropna(subset=["LAMBERT_X", "LAMBERT_Y"])
    mairie = xy[xy["TYPEQU"] == "A129"].groupby("DEPCOM").agg(
        x=("LAMBERT_X", "first"), y=("LAMBERT_Y", "first"), epsg=("EPSG", "first"), name=("LIBCOM", "first"))
    centre = xy.groupby("DEPCOM").agg(x=("LAMBERT_X", "median"), y=("LAMBERT_Y", "median"),
                                      epsg=("EPSG", "first"), name=("LIBCOM", "first"))
    ref = mairie.combine_first(centre)
    logger.info(f"📍 Points de référence : {len(ref)} communes ({len(mairie)} mairies)")
    return ref


def nearest(df, ref):
    from scipy.spatial import cKDTree
    xy = df.dropna(subset=["LAMBERT_X", "LAMBERT_Y"])
    present = df.groupby(["DEPCOM", "TYPEQU"]).size()
    rows = []
    for key, svc in SERVICES.items():
        if not svc.get("distance"):
            continue
        eq = xy[xy["TYPEQU"].isin(svc["types"])]
        have = set(present[present.index.get_level_values(1).isin(svc["types"])].index.get_level_values(0))
        missing = ref[~ref.index.isin(have)]
        for epsg, communes in missing.groupby("epsg"):
            pts = eq[eq["EPSG"] == epsg]
            if pts.empty:
                continue
            tree = cKDTree(pts[["LAMBERT_X", "LAMBERT_Y"]].to_numpy())
            dist, idx = tree.query(communes[["x", "y"]].to_numpy())
            near = pts.iloc[idx]
            rows.append(pd.DataFrame({
                "geo_code": communes.index, "year": YEAR, "service": key,
                "distance_km": np.round(dist / 1000, 1),
                "nearest_code": near["DEPCOM"].to_numpy(), "nearest_name": near["LIBCOM"].to_numpy(),
            }))
        logger.info(f"   {svc['label']} : {len(missing)} communes sans ce service")
    return pd.concat(rows, ignore_index=True)[NEAREST_COLUMNS]


def check(cnt, near, t):
    logger.info("🔎 Lignes de comptage par niveau : " + str(cnt.groupby("geo_level").size().to_dict()))
    fm = cnt[cnt.geo_level == "FRANCE"]["count"].sum()
    dep = cnt[(cnt.geo_level == "DEP") & ~cnt.geo_code.str.startswith("97")]["count"].sum()
    logger.info(f"🔎 Équipements en France métropolitaine : {fm:,.0f} (somme des départements {dep:,.0f})")
    logger.info(f"🔎 Types sans libellé : {sorted(set(cnt.typequ) - set(t.typequ))}")
    q = cnt[(cnt.geo_level == "COM") & (cnt.geo_code == "59484")].merge(t, on="typequ")
    logger.info(f"🔎 Quiévrechain : {q['count'].sum()} équipements, {q['count_qpv'].sum()} en QPV ; " +
                ", ".join(f"{r.label} {r['count']}" for _, r in q.sort_values("count", ascending=False).head(8).iterrows()))
    nq = near[near.geo_code == "59484"]
    for _, r in nq.iterrows():
        logger.info(f"   {SERVICES[r.service]['label']} le plus proche : {r.distance_km} km ({r.nearest_name})")
    logger.info(f"🔎 Distances : {len(near):,} lignes ; médiane par service : " +
                ", ".join(f"{s} {v:.1f} km" for s, v in near.groupby("service")["distance_km"].median().items()))


def _connect():
    import psycopg2
    from app.database import engine
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def _copy(cur, table, df, columns, where=""):
    buf = io.StringIO()
    out = df[columns].copy()
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].str.replace("\t", " ")
    out.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    cur.execute(f"DELETE FROM {table} {where}")
    cols = ", ".join('"%s"' % c for c in columns)
    cur.copy_expert(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
    logger.info(f"✅ {table} : {cur.rowcount:,} lignes importées")


def write(cnt, near, t):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            _copy(cur, "equipment_types", t, TYPE_COLUMNS)
            _copy(cur, "equipment_by_territory", cnt, COUNT_COLUMNS, f"WHERE year = {YEAR}")
            _copy(cur, "equipment_nearest", near, NEAREST_COLUMNS, f"WHERE year = {YEAR}")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            for table in ("equipment_types", "equipment_by_territory", "equipment_nearest"):
                cur.execute(f"ANALYZE {table}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier de la BPE")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    df = read(args.dir)
    t = types(args.dir)
    cnt = counts(df)
    near = nearest(df, reference_points(df))
    check(cnt, near, t)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(cnt, near, t)
        logger.info("🏁 Import terminé")
