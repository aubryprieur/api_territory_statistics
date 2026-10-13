"""
Import de l'impôt sur le revenu par collectivité territoriale (DGFiP — IRCOM) dans tax_households_by_territory.

Sources (data/revenues/ircom_<année d'imposition>_revenus_<année de revenus>/) :
  - ircom_communes_complet_revenus_<N>.xlsx : une ligne « Total » par commune (arrondissements pour Paris, Lyon,
    Marseille) et, pour les communes de plus de 2 000 foyers environ, une ligne par tranche de revenu fiscal de
    référence (RFR) ; « n.c. » = secret fiscal ;
  - departemental/<dir>.xls (ou departemental.zip), regional/<région>.xls (ou regional.zip) : tranches et total
    du département (code direction DGFiP : 590, 2A0…) et de la région.
Codes : commune Insee = 2 premiers caractères de la direction + code commune (592 / 484 → 59484 ; 754 / 101 → 75101).

Mesures (année = année des revenus) : households (foyers fiscaux), rfr (RFR, milliers d'euros), net_tax (impôt net,
milliers d'euros), taxed_households, wage_households, pension_households, et foyers par tranche de RFR :
hh_0_10k, hh_10_12k, hh_12_15k, hh_15_20k, hh_20_30k, hh_30_50k, hh_50_100k, hh_100k_plus.
Niveaux : COM (Paris, Lyon, Marseille = somme des arrondissements), ARM, EPCI (somme des communes du COG 2024 ;
tranches seulement si toutes les communes sont détaillées), DEP (fichiers départementaux), REG (fichiers régionaux),
FRANCE 'FM' (somme des 13 régions métropolitaines).

Lecture des .xls : nécessite xlrd (./venv/bin/pip install xlrd).

Usage :
    python scripts/import_tax_households_by_territory.py --dry-run
    python scripts/import_tax_households_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import re
import sys
import unicodedata
import zipfile

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/revenues"
COG = "data/geography/COG_au_01-01-2024.csv"
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}
TOTALS = ["households", "rfr", "net_tax", "taxed_households", "wage_households", "pension_households"]
BRACKETS = ["hh_0_10k", "hh_10_12k", "hh_12_15k", "hh_15_20k", "hh_20_30k", "hh_30_50k", "hh_50_100k", "hh_100k_plus"]
MEASURES = TOTALS + BRACKETS
COLUMNS = KEY + MEASURES
RAW = ["tranche", "households", "rfr", "net_tax", "taxed_households", "rfr_taxed", "wage_households", "wages",
       "pension_households", "pensions"]
REGIONS = {"auvergne-rhone-alpes": "84", "bourgogne-franche-comte": "27", "bretagne": "53", "centre-val-de-loire": "24",
           "corse": "94", "grand-est": "44", "hauts-de-france": "32", "ile-de-france": "11", "normandie": "28",
           "nouvelle-aquitaine": "75", "occitanie": "76", "paca": "93", "pays-de-la-loire": "52"}


def bracket_of(label):
    """Libellé de tranche → colonne (None pour le total ou les sous-tranches au-delà de 100 000 €)."""
    s = unicodedata.normalize("NFKD", str(label)).encode("ascii", "ignore").decode().lower().replace(" ", "")
    if s.startswith("total"):
        return "total"
    table = [("0a10000", "hh_0_10k"), ("10001a12000", "hh_10_12k"), ("12001a15000", "hh_12_15k"),
             ("15001a20000", "hh_15_20k"), ("20001a30000", "hh_20_30k"), ("30001a50000", "hh_30_50k"),
             ("50001a100000", "hh_50_100k"), ("+de100000", "hh_100k_plus"), ("plusde100000", "hh_100k_plus")]
    for key, col in table:
        if s.startswith(key):
            return col
    return None


def to_num(s):
    return pd.to_numeric(s.astype(str).str.replace(" ", "").str.replace(",", "."), errors="coerce")


def summary_table(raw, first_col=1):
    """Tableau de synthèse d'un fichier régional (tranche en colonne B) ou départemental (tranche en colonne E,
    lignes du département avant celles des communes) → une ligne de mesures."""
    t = raw.iloc[:, first_col:first_col + 10].copy()
    t.columns = RAW
    t["col"] = t["tranche"].map(bracket_of)
    t = t[t["col"].notna()].reset_index(drop=True)
    ends = t.index[t["col"] == "total"]
    if len(ends):
        t = t.loc[:ends[0]]  # premier bloc : le territoire lui-même
    t = t.drop_duplicates("col")
    row = {}
    total = t[t["col"] == "total"]
    if total.empty:
        return None
    total = total.iloc[0]
    for m in TOTALS:
        row[m] = to_num(pd.Series([total[m]])).iloc[0]
    for _, r in t[t["col"] != "total"].iterrows():
        row[r["col"]] = to_num(pd.Series([r["households"]])).iloc[0]
    return row


def read_xls_files(folder, zip_path):
    """{nom de fichier sans extension: DataFrame brut}, depuis un dossier ou un zip."""
    out = {}
    if os.path.isdir(folder):
        for path in sorted(glob.glob(os.path.join(folder, "*.xls"))):
            out[os.path.splitext(os.path.basename(path))[0]] = pd.read_excel(path, header=None, dtype=str)
    elif os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path) as z:
            for name in sorted(z.namelist()):
                if name.lower().endswith(".xls"):
                    out[os.path.splitext(os.path.basename(name))[0]] = pd.read_excel(io.BytesIO(z.read(name)), header=None, dtype=str)
    return out


def read_communes(path):
    raw = pd.read_excel(path, header=None, dtype=str)
    start = raw.index[raw.iloc[:, 1].astype(str).str.strip() == "Dép."][0] + 2
    df = raw.iloc[start:, 1:14].copy()
    df.columns = ["dir", "com"] + ["lib"] + RAW
    df = df[df["dir"].notna() & df["com"].notna() & (df["dir"].str.strip() != "B31")]
    df["code"] = df["dir"].str.strip().str[:2] + df["com"].str.strip().str.zfill(3)
    df["col"] = df["tranche"].map(bracket_of)
    tot = df[df["col"] == "total"].set_index("code")
    out = pd.DataFrame({m: to_num(tot[m]) for m in TOTALS})
    det = df[df["col"].notna() & (df["col"] != "total")]
    det = det.assign(n=to_num(det["households"])).pivot_table(index="code", columns="col", values="n", aggfunc="sum")
    out = out.join(det.reindex(columns=BRACKETS))
    return out.reset_index().rename(columns={"code": "geo_code"})


def read_year(folder, year):
    logger.info(f"📖 {folder} (revenus {year})")
    com = read_communes(glob.glob(os.path.join(folder, "ircom_communes_complet_revenus_*.xlsx"))[0])
    logger.info(f"   {len(com):,} communes ou arrondissements, dont {com['hh_0_10k'].notna().sum():,} détaillés par tranche")
    deps = []
    for name, raw in read_xls_files(os.path.join(folder, "departemental"), os.path.join(folder, "departemental.zip")).items():
        row = summary_table(raw, first_col=4)
        if row:
            code = name[:2] if not name.startswith("97") else name[:3]
            deps.append({"geo_code": code, **row})
    regs = []
    for name, raw in read_xls_files(os.path.join(folder, "regional"), os.path.join(folder, "regional.zip")).items():
        if name in REGIONS:
            row = summary_table(raw)
            if row:
                regs.append({"geo_code": REGIONS[name], **row})
    logger.info(f"   {len(deps)} départements, {len(regs)} régions métropolitaines")
    return com, pd.DataFrame(deps), pd.DataFrame(regs)


def build(base_dir):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    epci = dict(zip(geo["CODGEO"], geo["EPCI"]))
    known = set(geo["CODGEO"])
    parts = []
    for folder in sorted(glob.glob(os.path.join(base_dir, "ircom_*_revenus_*"))):
        year = int(re.search(r"revenus_(\d{4})", folder).group(1))
        com, dep, reg = read_year(folder, year)
        is_arm = com["geo_code"].str[:3].isin(ARM_PARENT) & ~com["geo_code"].isin(ARM_PARENT.values())
        arm = com[is_arm]
        parents = (arm.assign(geo_code=arm["geo_code"].str[:3].map(ARM_PARENT))
                   .groupby("geo_code")[MEASURES].sum(min_count=1).reset_index())
        c = pd.concat([com[~is_arm], parents], ignore_index=True)
        unknown = c[~c["geo_code"].isin(known)]
        logger.info(f"   codes absents du COG 2024 : {len(unknown)} {list(unknown['geo_code'][:8])}")
        parts.append(c.assign(geo_level="COM", year=year))
        parts.append(arm.assign(geo_level="ARM", year=year))
        e = c.assign(epci=c["geo_code"].map(epci))
        e = e[e["epci"].notna() & (e["epci"] != "ZZZZZZZZZ")]
        eg = e.groupby("epci")[TOTALS].sum(min_count=1)
        complete = e.groupby("epci")["hh_0_10k"].apply(lambda s: s.notna().all())
        eb = e.groupby("epci")[BRACKETS].sum(min_count=1).where(complete, None)
        parts.append(eg.join(eb).reset_index().rename(columns={"epci": "geo_code"}).assign(geo_level="EPCI", year=year))
        parts.append(dep.assign(geo_level="DEP", year=year))
        parts.append(reg.assign(geo_level="REG", year=year))
        fm = reg[MEASURES].sum(min_count=1).to_frame().T.assign(geo_code="FM", geo_level="FRANCE", year=year)
        if len(reg) != 13:
            logger.warning(f"   ⚠️ {len(reg)} régions lues au lieu de 13 : France métropolitaine incomplète")
        parts.append(fm)
    data = pd.concat(parts, ignore_index=True).reindex(columns=COLUMNS)
    return data.sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Lignes par niveau : " + str(data.groupby(["geo_level", "year"]).size().to_dict()))
    logger.info(f"🔎 Doublons : {data.duplicated(KEY).sum()}")
    full = data[data[BRACKETS].notna().all(axis=1)]
    gap = (full[BRACKETS].sum(axis=1) - full["households"]).abs() / full["households"]
    logger.info(f"🔎 Écart relatif somme des tranches / foyers : max {gap.max():.4f}, > 1 % : {(gap > 0.01).sum()} lignes "
                + str(full.loc[gap.sort_values().index[-3:], ['geo_level', 'geo_code', 'year']].values.tolist()))
    for level, code in (("COM", "59484"), ("COM", "75056"), ("EPCI", "245901160"), ("DEP", "59"), ("REG", "32"),
                        ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)].set_index("year")
        if r.empty:
            logger.info(f"🔎 {level} {code} : absent")
            continue
        txt = []
        for y, x in r.iterrows():
            low = x["hh_0_10k"] / x["households"] * 100 if pd.notna(x["hh_0_10k"]) else float("nan")
            txt.append(f"{y} : {x['households']:,.0f} foyers, imposés {x['taxed_households'] / x['households'] * 100:.1f} %, "
                       f"RFR moyen {x['rfr'] * 1000 / x['households']:,.0f} €, retraites {x['pension_households'] / x['households'] * 100:.1f} %, "
                       f"< 10 000 € {low:.1f} %")
        logger.info(f"🔎 {level} {code} : " + " | ".join(txt))


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
            cur.execute("DELETE FROM tax_households_by_territory")
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(f"COPY tax_households_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount:,} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE tax_households_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR)
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = build(args.dir)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
