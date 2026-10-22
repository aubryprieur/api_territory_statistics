"""
Import des indicateurs de l'Observatoire interrégimes des situations de fragilité (Géofragilité : Assurance
maladie, Assurance retraite, MSA) et de l'APL (ANCT) dans fragilities_by_territory.

Source : data/health/fragilites/ — un fichier par indicateur et par niveau (« … - commune.csv », « … - epci.csv »,
« … - departement.csv », « … - region.csv » ; CSV « ; », 2 lignes d'en-tête, colonnes Code ; Libellé ; valeur ;
« N/A - secret statistique » pour les petits effectifs). APL : apl-*-{communes,epci,departement,region}.xlsx
(ANCT, en-tête ligne 5 : codgeo, libgeo, an, valeur ; dernière année gardée).

Une ligne par (geo_level, geo_code) ; year = 2025 (millésime Géofragilité ; APL 2024, voir apl_year).
Ligne France (geo_code FM) : valeurs nationales relevées sur les cartes du site (data/health/fragilites/france.csv,
colonnes indicator ; … ; valeur_france ; perimetre — France entière pour Géofragilité, métropole pour l'APL ANCT).
Une case vide retombe sur la moyenne des 13 régions métropolitaines pondérée par la population 2023 (lue en base).
Fichiers MSA seuls non retenus (secret statistique pour 50 à 99 % des communes) : on garde l'interrégime quand il
existe, sinon le régime général (RG).

Usage :
    python scripts/import_fragilities_by_territory.py --dry-run
    python scripts/import_fragilities_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import sys
import unicodedata

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/health/fragilites"
YEAR, APL_YEAR = 2025, 2024
METRO_REGIONS = ["11", "24", "27", "28", "32", "44", "52", "53", "75", "76", "84", "93", "94"]
# indicateur : motif (minuscules, sans accents) que doit contenir le nom de fichier
FILES = {
    "no_gp_rate": "sans medecin traitant declare de l'interregime",
    "ald_rate": "en ald de l'interregime",
    "invalidity_rate": "pension d'invalidite de l'interregime",
    "c2s_rate": "part-css-rg-toute population",
    "no_dentist_rate": "consultant dentiste sur les 24 derniers mois",
    "no_colorectal_screening_rate": "depistage cancer colorectal",
    "no_cervical_screening_rate": "depistage cancer col de l'uterus",
    "no_mammography_rate": "mammographie",
    "no_gynecologist_rate": "gynecologue",
    "no_flu_vaccine_65p_rate": "65 ans et plus n'ayant pas eu un acte de vag",
    "no_flu_vaccine_75p_rate": "vag sur les 24 derniers mois 2025 - 75 ans",
}
APL = {"apl_dentists": "apl-dentistes", "apl_gp_under65": "apl-medecin-moins-65ans"}
MEASURES = list(FILES) + list(APL)
COLUMNS = ["geo_level", "geo_code", "year"] + MEASURES
LEVELS = {"commune": "COM", "epci": "EPCI", "departement": "DEP", "region": "REG"}


def norm(s):
    s = s.replace("’", "'").replace("`", "'")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def level_of(name):
    n = norm(name)
    for key, level in LEVELS.items():
        if n.rstrip(".csvxl").endswith(key) or n.rstrip(".csvxl").endswith(key + "s") or f"-{key}" in n or f"- {key}" in n:
            return level
    return None


def read(d):
    files = os.listdir(d)
    frames = {}
    for ind, pattern in FILES.items():
        hits = [f for f in files if f.endswith(".csv") and pattern in norm(f).replace("’", "'")]
        for f in hits:
            level = level_of(f)
            if not level:
                continue
            df = pd.read_csv(os.path.join(d, f), sep=";", skiprows=2, dtype=str, encoding="utf-8-sig")
            s = pd.to_numeric(df.iloc[:, 2].str.replace(",", "."), errors="coerce")
            frames.setdefault(level, []).append(pd.Series(s.values, index=df["Code"].str.strip(), name=ind))
        if not hits:
            logger.warning(f"   ⚠️ aucun fichier pour {ind}")
    for ind, prefix in APL.items():
        for f in [f for f in files if f.startswith(prefix) and f.endswith(".xlsx")]:
            level = level_of(f)
            df = pd.read_excel(os.path.join(d, f), header=4, dtype=str)
            df = df[pd.to_numeric(df["an"], errors="coerce") == APL_YEAR]
            s = pd.to_numeric(df.iloc[:, 3].str.replace(",", "."), errors="coerce")
            frames.setdefault(level, []).append(pd.Series(s.values, index=df["codgeo"].str.strip(), name=ind))
    parts = []
    for level, series in frames.items():
        w = pd.concat(series, axis=1)
        w = w.T.groupby(level=0).first().T if w.columns.duplicated().any() else w
        w = w.reset_index().rename(columns={"index": "geo_code"})
        w["geo_level"] = level
        parts.append(w)
        logger.info(f"📖 {level} : {len(w):,} territoires, {w.columns.size - 2} indicateurs")
    data = pd.concat(parts, ignore_index=True)
    data["year"] = YEAR
    return data.reindex(columns=COLUMNS)


def france_reference(d):
    """Valeurs nationales publiées sur le site (france.csv), {indicateur: float}."""
    path = os.path.join(d, "france.csv")
    if not os.path.exists(path):
        return {}
    ref = pd.read_csv(path, sep=";", dtype=str)
    out = {}
    for _, r in ref.iterrows():
        v = str(r.get("valeur_france") or "").strip().replace(",", ".")
        if r["indicator"] in MEASURES and v and v.lower() != "nan":
            out[r["indicator"]] = float(v)
    return out


def france(data, pops, ref):
    reg = data[(data.geo_level == "REG") & data.geo_code.isin(METRO_REGIONS)].copy()
    reg["w"] = reg["geo_code"].map(pops)
    row = {"geo_level": "FRANCE", "geo_code": "FM", "year": YEAR}
    for m in MEASURES:
        if m in ref:
            row[m] = ref[m]
            continue
        r = reg[reg[m].notna() & reg["w"].notna()]
        row[m] = round((r[m] * r["w"]).sum() / r["w"].sum(), 2) if len(r) else None
        logger.info(f"ℹ️ {m} : pas de valeur nationale dans france.csv, moyenne pondérée des régions = {row[m]}")
    return pd.DataFrame([row])[COLUMNS]


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(['geo_level', 'geo_code']).sum()}")
    com = data[data.geo_level == "COM"]
    logger.info("🔎 Communes avec valeur (hors secret) : " + ", ".join(f"{m} {com[m].notna().mean():.0%}" for m in MEASURES))
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("REG", "32"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if not r.empty:
            logger.info(f"🔎 {level} {code} : " + ", ".join(f"{m}={r.iloc[0][m]}" for m in MEASURES))


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def region_populations(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT geo_code, pop FROM population_by_territory WHERE geo_level = 'REG' AND year = 2023")
        return {c: float(p) for c, p in cur.fetchall() if p}


def write(conn, data):
    buf = io.StringIO()
    data[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fragilities_by_territory")
            cols = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY fragilities_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    data = read(DIR)
    ref = france_reference(DIR)
    logger.info(f"🇫🇷 Valeurs nationales lues dans france.csv : {len(ref)}/{len(MEASURES)}")
    if args.dry_run:
        data = pd.concat([data, france(data, {}, ref)], ignore_index=True)
        check(data)
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        conn = _connect()
        try:
            data = pd.concat([data, france(data, region_populations(conn), ref)], ignore_index=True)
            check(data)
            write(conn, data)
        finally:
            conn.close()
        logger.info("🏁 Import terminé")
