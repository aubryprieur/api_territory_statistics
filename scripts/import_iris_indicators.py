"""
Import d'indicateurs IRIS hors recensement dans iris_indicators (format long), pour les cartes IRIS.

Une ligne par (geo_level, geo_code, year, indicator) : value, count, total.
  - geo_level 'IRIS' : valeur de l'IRIS ;
  - geo_level 'COM'  : valeur de référence de la commune quand l'indicateur n'est pas additif (médiane, taux de
    pauvreté) ; pour les indicateurs additifs (count / total), la commune est la somme de ses IRIS (calcul dans l'API).

Sources (dossier data/) :
  - revenues/iris/BASE_TD_FILO_DISP_IRIS_<N>.csv (Insee Filosofi, revenus disponibles, 2017-2021) et
    revenues/commune/cc_filosofi_<N>_COM.csv (référence communale) :
      median_income (€), poverty_rate (%), social_benefits_share (% du revenu disponible) ;
  - health/c2s/beneficiaires_CNAM_01-01-<N>_Iris_csv/data_CNAM<N>_IRIS.csv (Cnam, 2022, 2025) :
      c2s_free_rate = C2S sans participation / assurés du régime général ;
  - social_housing/RPLS_01-01-2025_Iris/data_RPLS2025_Iris.csv (SDES, RPLS au 1er janvier 2025) :
      social_turnover_rate, social_vacancy_rate (count = taux × logements sociaux, total = logements sociaux) ;
  - employment_seekers/DEFM<N>*/…iris…csv (France Travail / Insee, demandeurs d'emploi au 31 décembre 2021-2023) :
      job_seekers_abc (count = demandeurs A, B, C ; le dénominateur, actifs de 15-64 ans du recensement 2022, est
      ajouté par l'API).
Les fichiers « au niveau Iris » ne couvrent que les communes découpées en IRIS.

Usage :
    python scripts/import_iris_indicators.py --dry-run
    python scripts/import_iris_indicators.py
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

COLUMNS = ["geo_level", "geo_code", "year", "indicator", "value", "count", "total"]


def read(path):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, sep=";", dtype=str, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(path)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", ".").str.strip(), errors="coerce")


def rows(level, codes, year, indicator, value=None, count=None, total=None):
    df = pd.DataFrame({"geo_code": codes.astype(str).str.strip()})
    df["geo_level"], df["year"], df["indicator"] = level, year, indicator
    df["value"] = value.values if value is not None else None
    df["count"] = count.values if count is not None else None
    df["total"] = total.values if total is not None else None
    return df[COLUMNS]


def filosofi():
    parts = []
    for path in sorted(glob.glob("data/revenues/iris/BASE_TD_FILO_DISP_IRIS_*.csv")):
        year = int(re.search(r"(\d{4})", os.path.basename(path)).group(1))
        yy = str(year)[2:]
        d = read(path)
        d = d[d["IRIS"].notna()]
        for ind, col in (("median_income", f"DISP_MED{yy}"), ("poverty_rate", f"DISP_TP60{yy}"),
                         ("social_benefits_share", f"DISP_PPSOC{yy}")):
            if col in d:
                parts.append(rows("IRIS", d["IRIS"].str.zfill(9), year, ind, value=num(d[col])))
        com_path = f"data/revenues/commune/cc_filosofi_{year}_COM.csv"
        if os.path.exists(com_path):
            c = read(com_path)
            for ind, col in (("median_income", f"MED{yy}"), ("poverty_rate", f"TP60{yy}"),
                             ("social_benefits_share", f"PPSOC{yy}")):
                if col in c:
                    parts.append(rows("COM", c["CODGEO"].str.zfill(5), year, ind, value=num(c[col])))
        logger.info(f"📖 Filosofi {year} : {len(d):,} IRIS")
    return parts


def c2s():
    parts = []
    for path in sorted(glob.glob("data/health/c2s/*/data_CNAM*_IRIS.csv")):
        year = int(re.search(r"CNAM(\d{4})", path).group(1))
        d = read(path)
        parts.append(rows("IRIS", d["CODGEO"].str.zfill(9), year, "c2s_free_rate",
                          count=num(d["C_C2SNP"]), total=num(d["C"])))
        logger.info(f"📖 C2S {year} : {len(d):,} IRIS")
    return parts


def rpls():
    parts = []
    for path in sorted(glob.glob("data/social_housing/RPLS_01-01-*_Iris/data_RPLS*_Iris.csv")):
        year = int(re.search(r"RPLS(\d{4})", os.path.basename(path)).group(1))
        d = read(path)
        n = num(d["nbLsPls"])
        for ind, col in (("social_turnover_rate", "txRot"), ("social_vacancy_rate", "txVac")):
            parts.append(rows("IRIS", d["CodGeo"].str.zfill(9), year, ind, count=num(d[col]) * n / 100, total=n))
        logger.info(f"📖 RPLS {year} : {len(d):,} IRIS")
    return parts


def defm():
    parts = []
    for path in sorted(glob.glob("data/employment_seekers/DEFM*/data_DEFM*_*[Ii][Rr][Ii][Ss].csv")):
        if re.search(r"_com\.csv$", path, re.I):
            continue
        year = int(re.search(r"DEFM(\d{4})", path).group(1))
        d = read(path)
        parts.append(rows("IRIS", d["CODGEO"].str.zfill(9), year, "job_seekers_abc", count=num(d["ABC"])))
        logger.info(f"📖 DEFM {year} : {len(d):,} IRIS ({os.path.basename(path)})")
    return parts


def build():
    data = pd.concat(filosofi() + c2s() + rpls() + defm(), ignore_index=True)
    data = data[data["value"].notna() | data["count"].notna()]
    return data


def check(data):
    logger.info("🔎 Lignes : " + str(data.groupby(["indicator", "geo_level", "year"]).size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(['geo_level', 'geo_code', 'year', 'indicator']).sum()}")
    q = data[data["geo_code"].str.startswith("59484")]
    for _, r in q.sort_values(["indicator", "year", "geo_code"]).iterrows():
        logger.info(f"   {r['indicator']} {r['year']} {r['geo_level']} {r['geo_code']} : value={r['value']} count={r['count']} total={r['total']}")


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
    buf = io.StringIO()
    out[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM iris_indicators")
            cols = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY iris_indicators ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE iris_indicators")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    data = build()
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
