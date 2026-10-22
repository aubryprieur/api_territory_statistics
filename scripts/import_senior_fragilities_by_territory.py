"""
Import des indicateurs « Seniors » de l'Observatoire interrégimes des situations de fragilité (Géofragilité :
Assurance maladie, Assurance retraite, MSA) dans senior_fragilities_by_territory.

Source : data/seniors/fragilites/ — exports du site (CSV « ; », 2 lignes d'en-tête, colonnes Code ; Libellé ; valeur ;
« N/A - secret statistique » ou « N/A - résultat non disponible » → NULL). Population : retraités et assurés de
55 ans ou plus, interrégime, millésime 2025 (score de non-recours aux soins : 2024).
  - parts et scores : fichiers « … - commune / epci / departement / region.csv », repris tels quels ;
  - nombres (communes seulement) : retraités à risque de fragilité sociale et retraités (base du score) → part des
    retraités à risque ; retraités 2017 et 2025 → évolution. EPCI, département, région et France = sommes des
    communes (COG 2024) ayant une valeur (secret statistique dans les plus petites communes).
Ligne France (geo_code FM, France entière, outre-mer compris) : valeurs relevées sur les cartes du site
(data/seniors/fragilites/france.csv) ; case vide → moyenne des départements pondérée par le nombre de retraités.

Usage :
    python scripts/import_senior_fragilities_by_territory.py --dry-run
    python scripts/import_senior_fragilities_by_territory.py
"""
import argparse
import io
import logging
import os
import sys
import unicodedata

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/seniors/fragilites"
COG = "data/geography/COG_au_01-01-2024.csv"
YEAR = 2025
# indicateur : motif (minuscules, sans accents) que doit contenir le nom de fichier
RATES = {
    "social_fragility_score": "score moyen de la fragilite sociale des retraites de l'interregime",
    "care_nonuse_score": "score moyen de fragilite liee au non recours aux soins des seniors ir",
    "min_old_age_rate": "part des retraites au minimum vieillesse de l'interregime",
    "csg_exempt_rate": "part des retraites de l'interregime exoneres de la csg",
    "csg_low_rate": "part des retraites de l'interregime assujettis a la csg au taux faible",
    "survivor_pension_rate": "part des beneficiaires d'une pension de reversion de l'interregime",
    "invalidity_inaptitude_rate": "part des retraites beneficiaires d'une pension ex invalide",
    "incomplete_career_rate": "part des retraites de l'interregime partis a l'age du taux plein",
    "css_free_rate": "part des seniors de l'interregime beneficiant de la css non participative",
    "no_care_rate": "part des seniors sans recours aux soins de l'interregime",
    "no_gp_rate": "part des seniors sans medecin traitant de l'interregime",
    "ald_rate": "part des seniors en ald de l'interregime",
}
COUNTS = {  # fichiers communaux
    "at_risk": "nombre de retraites a risque de fragilite sociale de l'interregime 2025",
    "base": "nombre de retraites de l'interregime 2025",
    "r2025": "nb de retraites de l'interregime 2025",
    "r2017": "nb de retraites de l'interregime 2017",
}
MEASURES = ["social_fragility_score", "care_nonuse_score", "at_risk_share", "at_risk_count", "retirees_count",
            "retirees_change_rate", "min_old_age_rate", "csg_exempt_rate", "csg_low_rate", "survivor_pension_rate",
            "invalidity_inaptitude_rate", "incomplete_career_rate", "css_free_rate", "no_care_rate", "no_gp_rate",
            "ald_rate"]
COLUMNS = ["geo_level", "geo_code", "year"] + MEASURES
LEVELS = {"commune": "COM", "epci": "EPCI", "departement": "DEP", "region": "REG"}


def norm(s):
    s = s.replace("’", "'").replace("`", "'")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def level_of(name):
    stem = norm(name)[:-4].strip()
    for key, level in LEVELS.items():
        if stem.endswith(key):
            return level
    return None


def read_file(path):
    df = pd.read_csv(path, sep=";", skiprows=2, dtype=str, encoding="utf-8-sig")
    values = pd.to_numeric(df.iloc[:, 2].str.replace(",", "."), errors="coerce")
    return pd.Series(values.values, index=df.iloc[:, 0].str.strip())


def find(files, pattern, level):
    hits = [f for f in files if f.endswith(".csv") and pattern in norm(f) and level_of(f) == level]
    if len(hits) > 1:
        raise SystemExit(f"Plusieurs fichiers pour « {pattern} » ({level}) : {hits}")
    return hits[0] if hits else None


def read_rates(files):
    frames = {}
    for level in LEVELS.values():
        cols = {}
        for ind, pattern in RATES.items():
            f = find(files, pattern, level)
            if f:
                cols[ind] = read_file(os.path.join(DIR, f))
            else:
                logger.warning(f"   ⚠️ aucun fichier {level} pour {ind}")
        frames[level] = pd.DataFrame(cols)
        logger.info(f"📖 {level} : {len(frames[level]):,} territoires, {len(cols)} parts et scores")
    return frames


def read_counts(files):
    cols = {}
    for key, pattern in COUNTS.items():
        f = find(files, pattern, "COM")
        if not f:
            raise SystemExit(f"Fichier communal manquant : {pattern}")
        cols[key] = read_file(os.path.join(DIR, f))
    c = pd.DataFrame(cols)
    c.index = c.index.str.zfill(5)
    return c


def count_measures(c):
    """Part à risque, nombre de retraités et évolution 2017-2025 à partir de sommes de communes."""
    risk = c[["at_risk", "base"]].dropna()
    evo = c[["r2017", "r2025"]].dropna()
    out = {
        "at_risk_count": risk["at_risk"].sum(),
        "at_risk_share": round(100 * risk["at_risk"].sum() / risk["base"].sum(), 2) if risk["base"].sum() else None,
        "retirees_count": c["base"].sum(min_count=1),
        "retirees_change_rate": round(100 * (evo["r2025"].sum() / evo["r2017"].sum() - 1), 2) if evo["r2017"].sum() else None,
    }
    return out


def aggregate_counts(c):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    geo["DEP"] = geo["DEP"].str.zfill(2)
    geo["REG"] = geo["REG"].str.zfill(2)
    geo = geo.set_index("CODGEO")
    missing = c.index.difference(geo.index)
    logger.info(f"   Codes communaux absents du COG 2024 (comptés en France seulement) : {len(missing)}")
    c = c.join(geo[["EPCI", "DEP", "REG"]])
    rows = []
    # communes : valeurs propres
    for code, r in c.iterrows():
        share = round(100 * r.at_risk / r.base, 2) if pd.notna(r.at_risk) and pd.notna(r.base) and r.base else None
        change = round(100 * (r.r2025 / r.r2017 - 1), 2) if pd.notna(r.r2017) and pd.notna(r.r2025) and r.r2017 else None
        rows.append({"geo_level": "COM", "geo_code": code, "at_risk_count": r.at_risk, "at_risk_share": share,
                     "retirees_count": r.base, "retirees_change_rate": change})
    for level, col in (("EPCI", "EPCI"), ("DEP", "DEP"), ("REG", "REG")):
        sub = c[c[col].notna() & (c[col] != "ZZZZZZZZZ")]
        for code, g in sub.groupby(col):
            rows.append({"geo_level": level, "geo_code": code, **count_measures(g)})
    rows.append({"geo_level": "FRANCE", "geo_code": "FM", **count_measures(c)})
    return pd.DataFrame(rows)


def france_reference():
    path = os.path.join(DIR, "france.csv")
    if not os.path.exists(path):
        return {}
    ref = pd.read_csv(path, sep=";", dtype=str)
    out = {}
    for _, r in ref.iterrows():
        v = str(r.get("valeur_france") or "").strip().replace(",", ".")
        if r["indicator"] in RATES and v and v.lower() != "nan":
            out[r["indicator"]] = float(v)
    return out


def france_rates(dep_rates, dep_retirees, ref):
    row = {}
    w = dep_retirees.reindex(dep_rates.index)
    for m in RATES:
        r = dep_rates[m].dropna()
        ww = w.reindex(r.index).dropna()
        weighted = round((r[ww.index] * ww).sum() / ww.sum(), 2) if len(ww) else None
        if m in ref:
            row[m] = ref[m]
            logger.info(f"   🇫🇷 {m} : publié {ref[m]} (contrôle : moyenne pondérée des départements {weighted})")
        else:
            row[m] = weighted
            logger.info(f"   ℹ️ {m} : pas de valeur publiée dans france.csv → moyenne pondérée des départements {weighted}")
    return row


def build():
    files = os.listdir(DIR)
    rates = read_rates(files)
    counts = aggregate_counts(read_counts(files))
    parts = []
    for level, df in rates.items():
        df = df.copy()
        df.index = df.index.str.zfill(5 if level == "COM" else 2) if level in ("COM", "DEP", "REG") else df.index
        parts.append(df.rename_axis("geo_code").reset_index().assign(geo_level=level))
    data = pd.concat(parts, ignore_index=True)
    data = data.merge(counts, on=["geo_level", "geo_code"], how="outer")
    dep = data[data.geo_level == "DEP"].set_index("geo_code")
    fr = france_rates(dep[list(RATES)], dep["retirees_count"], france_reference())
    is_fr = data.geo_level == "FRANCE"
    for m, v in fr.items():
        data.loc[is_fr, m] = v
    data["year"] = YEAR
    return data.reindex(columns=COLUMNS)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(['geo_level', 'geo_code']).sum()}")
    com = data[data.geo_level == "COM"]
    logger.info("🔎 Communes avec valeur : " + ", ".join(f"{m} {com[m].notna().mean():.0%}" for m in MEASURES))
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


def write(conn, data):
    buf = io.StringIO()
    data[COLUMNS].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM senior_fragilities_by_territory")
            cols = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY senior_fragilities_by_territory ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    data = build()
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
