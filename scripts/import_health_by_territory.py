"""
Import des données de santé dans trois tables :

  health_professionals_by_territory  densité de professionnels de santé libéraux pour 100 000 habitants
      (Observatoire des territoires — ANCT : RPPS, Adeli, BPE 2025, recensement 2023), 16 professions,
      COM, EPCI, DEP, REG publiés ; FRANCE 'FM' = moyenne des régions métropolitaines pondérée par la population
      de référence (recensement 2023 : population totale, moins de 15 ans pour les pédiatres, femmes de 15 ans
      ou plus pour les gynécologues et sages-femmes). Sources : data/health/professionals/offre_sante_densite-*.xlsx
  health_insurance_by_territory      bénéficiaires du régime général de l'assurance maladie et de la
      complémentaire santé solidaire (C2S) au 1er janvier 2022 et 2025 (Cnam, diffusion Insee « données au niveau
      Iris »). Seules les ~1 900 communes découpées en IRIS sont publiées : COM, ARM ; EPCI, DEP, REG, FRANCE 'FM'
      = somme des communes publiées (communes à IRIS seulement), avec leur nombre (communes), pour la dernière
      édition seulement (les éditions ne couvrent pas les mêmes communes).
      Sources : data/health/c2s/beneficiaires_CNAM_01-01-<année>_Iris_csv/data_CNAM<année>_COM.csv
  ald_by_territory                   affections de longue durée (Cnam, régime général, 2024) : effectifs et taux
      standardisés pour 100 000 personnes protégées, par département ; FRANCE 'FE' (France entière) : prévalence
      nationale. Sources : data/health/ald/2024_ald-prevalentes*.xls

Usage :
    python scripts/import_health_by_territory.py --dry-run
    python scripts/import_health_by_territory.py
"""
import argparse
import glob
import io
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/health"
COG = "data/geography/COG_au_01-01-2024.csv"
KEY = ["geo_level", "geo_code", "year"]
ARM_PARENT = {"751": "75056", "693": "69123", "132": "13055"}

PROFESSIONS = {"medg": "gp", "inf": "nurse", "masskine": "physio", "chirdent": "dentist", "sgf": "midwife",
               "psycho": "psychologist", "pedia": "pediatrician", "gynec": "gynecologist", "psychi": "psychiatrist",
               "opht": "ophthalmologist", "card": "cardiologist", "derm": "dermatologist", "gastro": "gastroenterologist",
               "pneumo": "pulmonologist", "orl": "ent", "radio": "radiologist"}
PRO_COLUMNS = KEY + [f"{v}_density" for v in PROFESSIONS.values()]
WEIGHT = {"pediatrician": "pop_lt15", "gynecologist": "women_15p", "midwife": "women_15p"}

C2S_FIELDS = {"C": "insured", "C_H": "insured_men", "C_F": "insured_women", "C_17": "insured_lt18",
              "C_1824": "insured_18_24", "C_2549": "insured_25_49", "C_5059": "insured_50_59",
              "C_6074": "insured_60_74", "C_75": "insured_ge75",
              "C_C2SNP": "c2s_free", "C_17_C2SNP": "c2s_free_lt18", "C_1824_C2SNP": "c2s_free_18_24",
              "C_2549_C2SNP": "c2s_free_25_49", "C_5059_C2SNP": "c2s_free_50_59", "C_60_C2SNP": "c2s_free_ge60",
              "C_H_C2SNP": "c2s_free_men", "C_F_C2SNP": "c2s_free_women",
              "C_C2SP": "c2s_paid", "C_17_C2SP": "c2s_paid_lt18", "C_60_C2SP": "c2s_paid_ge60"}
C2S_COLUMNS = KEY + list(C2S_FIELDS.values()) + ["communes"]

ALD = {1: "stroke", 5: "heart_failure", 8: "diabetes", 13: "coronary", 14: "respiratory", 15: "alzheimer",
       16: "parkinson", 23: "psychiatric", 30: "cancer"}
ALD_COLUMNS = KEY + [f"{v}_{k}" for v in ALD.values() for k in ("count", "rate")]


def _pro_sheet(path):
    df = pd.read_excel(path, sheet_name="Data", header=4, dtype={"codgeo": str})
    df = df[df["offre_sante"].isin(PROFESSIONS)]
    wide = df.pivot_table(index=["codgeo", "an"], columns="offre_sante", values="densite", aggfunc="first").reset_index()
    wide = wide.rename(columns={"codgeo": "geo_code", "an": "year", **{k: f"{v}_density" for k, v in PROFESSIONS.items()}})
    return wide


def professionals(d, populations=None):
    parts = []
    for level, name in (("COM", "communes"), ("EPCI", "epci"), ("DEP", "departement"), ("REG", "region")):
        w = _pro_sheet(os.path.join(d, "professionals", f"offre_sante_densite-{name}.xlsx"))
        w["geo_level"] = level
        if level == "COM":
            w["geo_code"] = w["geo_code"].str.zfill(5)
            arm = w["geo_code"].str[:3].isin(ARM_PARENT) & ~w["geo_code"].isin(ARM_PARENT.values())
            w.loc[arm, "geo_level"] = "ARM"
        parts.append(w)
    data = pd.concat(parts, ignore_index=True)
    if populations is not None:
        reg = data[(data.geo_level == "REG") & (data.geo_code.str.len() == 2) & (data.geo_code.astype(int) > 10)]
        reg = reg.merge(populations, on="geo_code")
        fm = {"geo_level": "FRANCE", "geo_code": "FM", "year": int(reg["year"].max())}
        for v in PROFESSIONS.values():
            wcol = WEIGHT.get(v, "pop")
            ok = reg[f"{v}_density"].notna() & reg[wcol].notna()
            fm[f"{v}_density"] = round((reg.loc[ok, f"{v}_density"] * reg.loc[ok, wcol]).sum() / reg.loc[ok, wcol].sum(), 1)
        data = pd.concat([data, pd.DataFrame([fm])], ignore_index=True)
    else:
        logger.warning("   France métropolitaine non calculée (populations régionales indisponibles sans base)")
    return data.reindex(columns=PRO_COLUMNS)


def insurance(d):
    geo = pd.read_csv(COG, sep=";", dtype=str)
    geo["CODGEO"] = geo["CODGEO"].str.zfill(5)
    epci = dict(zip(geo["CODGEO"], geo["EPCI"]))
    reg = dict(zip(geo["CODGEO"], geo["REG"].str.zfill(2)))
    parts = []
    paths = sorted(glob.glob(os.path.join(d, "c2s", "*", "data_CNAM*_COM.csv")))
    latest = max(int(re.search(r"CNAM(\d{4})", p).group(1)) for p in paths)
    for path in paths:
        year = int(re.search(r"CNAM(\d{4})", path).group(1))
        df = pd.read_csv(path, sep=";", dtype=str)
        df = df[df["NOTE"].astype(str) == "0"]
        for c in C2S_FIELDS:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.rename(columns=C2S_FIELDS)
        df["geo_code"] = df["CODGEO"].str.zfill(5)
        df["year"] = year
        arm = df["geo_code"].str[:3].isin(ARM_PARENT) & ~df["geo_code"].isin(ARM_PARENT.values())
        com = df[~arm].assign(geo_level="COM", communes=1)
        parts += [com, df[arm].assign(geo_level="ARM", communes=1)]
        com = com.assign(EPCI=com["geo_code"].map(epci), REG=com["geo_code"].map(reg),
                         DEP=np.where(com["geo_code"].str.startswith("97"), com["geo_code"].str[:3], com["geo_code"].str[:2]),
                         FM=np.where(com["geo_code"].str.startswith("97"), None, "FM"))
        values = list(C2S_FIELDS.values()) + ["communes"]
        if year != latest:
            # Les éditions n'ont pas le même ensemble de communes (975 en 2022, 1 881 en 2025) : les agrégats ne
            # sont calculés que pour la dernière édition, l'évolution n'est lue qu'à la commune.
            logger.info(f"   C2S {year} : {len(com)} communes publiées (pas d'agrégat)")
            continue
        for level, col in (("EPCI", "EPCI"), ("DEP", "DEP"), ("REG", "REG"), ("FRANCE", "FM")):
            b = com[com[col].notna() & (com[col] != "ZZZZZZZZZ")]
            agg = b.groupby([col, "year"])[values].sum(min_count=1).reset_index().rename(columns={col: "geo_code"})
            parts.append(agg.assign(geo_level=level))
        logger.info(f"   C2S {year} : {len(com)} communes publiées")
    return pd.concat(parts, ignore_index=True).reindex(columns=C2S_COLUMNS)


def ald(d):
    path = os.path.join(d, "ald", "2024_ald-prevalentes-par-departement_serie-annuelle.xls")
    year = int(re.search(r"(\d{4})_ald", path).group(1))
    out = None
    for sheet, kind in ((0, "count"), (1, "rate")):
        df = pd.read_excel(path, sheet_name=sheet, header=1, dtype=str)
        df = df[df["Code département"].astype(str).str.match(r"^(\d{2,3}|2A|2B)$", na=False)]
        cols = {"Code département": "geo_code"}
        for c in df.columns:
            m = re.search(r"\(ALD(\d+)\)$", str(c))
            if m and int(m.group(1)) in ALD:
                cols[c] = f"{ALD[int(m.group(1))]}_{kind}"
        df = df[list(cols)].rename(columns=cols)
        for c in df.columns[1:]:
            df[c] = pd.to_numeric(df[c].str.replace("<10", "5", regex=False), errors="coerce")
        out = df if out is None else out.merge(df, on="geo_code")
    out["geo_level"], out["year"] = "DEP", year
    raw = pd.read_excel(os.path.join(d, "ald", "2024_ald-prevalentes_serie-annuelle.xls"), sheet_name=0, header=None, dtype=str)
    head = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Code"][0]
    nat = raw.iloc[head + 1:].copy()
    nat.columns = [str(c).strip() for c in raw.iloc[head]]
    nat = nat[pd.to_numeric(nat["Code"], errors="coerce").isin(ALD)]
    fe = {"geo_level": "FRANCE", "geo_code": "FE", "year": year}
    for _, r in nat.iterrows():
        k = ALD[int(float(r["Code"]))]
        fe[f"{k}_count"] = float(r["Effectif"])
        fe[f"{k}_rate"] = float(r["Prévalence pour 100 000"])
    return pd.concat([out, pd.DataFrame([fe])], ignore_index=True).reindex(columns=ALD_COLUMNS)


def regional_populations():
    """Population de référence des régions (recensement 2023) pour la moyenne France métropolitaine."""
    try:
        conn = _connect()
    except Exception as e:  # pas de base (dry-run hors du Mac)
        logger.warning(f"   Base indisponible : {e.__class__.__name__}")
        return None
    try:
        q = ("SELECT geo_code, pop, pop_lt15, pop_women - pop_lt15_women AS women_15p FROM population_by_territory "
             "WHERE geo_level = 'REG' AND year = 2023")
        return pd.read_sql(q, conn)
    finally:
        conn.close()


def check(pro, ins, ald_df):
    for name, data in (("professionnels", pro), ("C2S", ins), ("ALD", ald_df)):
        logger.info(f"🔎 {name} : lignes par niveau {data.groupby('geo_level').size().to_dict()} ; doublons {data.duplicated(KEY).sum()}")
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("REG", "32"), ("FRANCE", "FM")):
        r = pro[(pro.geo_level == level) & (pro.geo_code == code)]
        if not r.empty:
            r = r.iloc[0]
            logger.info(f"🔎 Professionnels {level} {code} : généralistes {r.gp_density}, infirmiers {r.nurse_density}, "
                        f"pédiatres {r.pediatrician_density}, psychiatres {r.psychiatrist_density} pour 100 000")
    for level, code in (("COM", "59484"), ("EPCI", "245901160"), ("DEP", "59"), ("FRANCE", "FM")):
        r = ins[(ins.geo_level == level) & (ins.geo_code == code)].sort_values("year")
        for _, x in r.iterrows():
            logger.info(f"🔎 C2S {level} {code} {x.year} : {x.c2s_free:,.0f} C2S gratuite + {x.c2s_paid:,.0f} participative "
                        f"sur {x.insured:,.0f} assurés ({x.c2s_free / x.insured * 100:.1f} % + {x.c2s_paid / x.insured * 100:.1f} %), "
                        f"{x.communes:.0f} commune(s)")
    for code in ("59", "FE"):
        r = ald_df[ald_df.geo_code == code].iloc[0]
        logger.info(f"🔎 ALD {code} : diabète {r.diabetes_rate}, cancers {r.cancer_rate}, psychiatrie {r.psychiatric_rate} pour 100 000")


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def _copy(cur, table, df, columns):
    out = df[columns].copy()
    out["year"] = out["year"].astype(int)
    buf = io.StringIO()
    out.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    cur.execute(f"DELETE FROM {table}")
    cols = ", ".join('"%s"' % c for c in columns)
    cur.copy_expert(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
    logger.info(f"✅ {table} : {cur.rowcount:,} lignes importées")


def write(pro, ins, ald_df):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            _copy(cur, "health_professionals_by_territory", pro, PRO_COLUMNS)
            _copy(cur, "health_insurance_by_territory", ins, C2S_COLUMNS)
            _copy(cur, "ald_by_territory", ald_df, ALD_COLUMNS)
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            for t in ("health_professionals_by_territory", "health_insurance_by_territory", "ald_by_territory"):
                cur.execute(f"ANALYZE {t}")
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

    logger.info("📖 Professionnels de santé")
    pro = professionals(args.dir, regional_populations())
    logger.info("📖 Complémentaire santé solidaire")
    ins = insurance(args.dir)
    logger.info("📖 Affections de longue durée")
    ald_df = ald(args.dir)
    check(pro, ins, ald_df)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(pro, ins, ald_df)
        logger.info("🏁 Import terminé")
