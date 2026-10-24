"""
Import des données carroyées Filosofi 2021 (Insee, revenus, pauvreté et niveau de vie, carreaux de 1 km, mise en
ligne en février 2026) dans grid_filosofi_1km.

Source : data/grid/carreaux_1km_met.csv (France métropolitaine ; les fichiers Martinique et La Réunion, dans d'autres
projections, ne sont pas importés). Colonnes Insee : idcar_1km (CRS3035RES1000mN{y}E{x}, coin inférieur gauche en
LAEA), i_est_1km (0 = valeurs réelles, 1 = carreau imputé car moins de 11 ménages, 2 = réel mais arrondi sous 11),
lcog_geo (communes touchées, codes accolés « 59484,59505 »), ind, men, men_pauv (tronqué à 80 % des ménages),
men_fmp, log_soc, ind_snv (somme des niveaux de vie winsorisés), ind_0_3, ind_80p.

Usage :
    python scripts/import_grid_filosofi.py --dry-run
    python scripts/import_grid_filosofi.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SRC = "data/grid/carreaux_1km_met.csv"
MEASURES = ["ind", "men", "men_pauv", "men_fmp", "log_soc", "ind_snv", "ind_0_3", "ind_80p"]
COLUMNS = ["idcar", "x", "y", "imputed", "communes"] + MEASURES


def read():
    d = pd.read_csv(SRC, dtype={"idcar_1km": str, "lcog_geo": str},
                    usecols=["idcar_1km", "i_est_1km", "lcog_geo"] + MEASURES)
    xy = d.idcar_1km.str.extract(r"^CRS3035RES1000mN(\d+)E(\d+)$")
    bad = xy[0].isna().sum()
    if bad:
        logger.warning(f"   ⚠️ {bad} identifiants hors format CRS3035RES1000mN…E… ignorés")
    d = d[xy[0].notna()].copy()
    d["y"] = xy[0].dropna().astype(int)
    d["x"] = xy[1].dropna().astype(int)
    d["communes"] = d.lcog_geo.fillna("").str.replace(" ", "").str.findall(r"\d[0-9AB]\d{3}")
    d = d.rename(columns={"idcar_1km": "idcar", "i_est_1km": "imputed"})
    logger.info(f"📖 {SRC} : {len(d):,} carreaux, {d.ind.sum():,.0f} habitants, {d.men.sum():,.0f} ménages ; "
                f"imputés : {(d.imputed == 1).mean():.0%} des carreaux, "
                f"{d.loc[d.imputed == 1, 'ind'].sum() / d.ind.sum():.1%} des habitants")
    return d[COLUMNS]


def check(d):
    q = d[d.communes.apply(lambda c: "59484" in c)]
    logger.info(f"🔎 Quiévrechain : {len(q)} carreaux touchant la commune, {q.ind.sum():,.0f} habitants dans ces carreaux")
    for _, r in q.iterrows():
        nv = r.ind_snv / r.ind if r.ind else None
        logger.info(f"     {r.idcar} {','.join(r.communes):<18} {r.ind:>7.0f} hab. ; niveau de vie moyen {nv:,.0f} € ; "
                    f"pauvres {100 * r.men_pauv / r.men if r.men else 0:.0f} % ; imputé {r.imputed}")


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(conn, d):
    buf = io.StringIO()
    for r in d.itertuples(index=False):
        vals = [r.idcar, str(r.x), str(r.y), "\\N" if pd.isna(r.imputed) else str(int(r.imputed)),
                "{" + ",".join(r.communes) + "}"]
        vals += ["\\N" if pd.isna(getattr(r, m)) else repr(float(getattr(r, m))) for m in MEASURES]
        buf.write("\t".join(vals) + "\n")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM grid_filosofi_1km")
            cur.copy_expert(f"COPY grid_filosofi_1km ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
                            buf)
            logger.info(f"✅ {cur.rowcount:,} carreaux importés")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    data = read()
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        conn = _connect()
        try:
            write(conn, data)
        finally:
            conn.close()
        logger.info("🏁 Import terminé")
