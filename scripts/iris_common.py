"""
Outils communs aux imports IRIS (scripts/import_iris_*.py) pour les millésimes anciens.

Les bases infracommunales de l'Insee n'ont pas toutes les mêmes colonnes selon le millésime :
  - avant 2020 environ, pas de LIBIRIS / DEP / REG : le nom de l'IRIS, le département et la région sont repris de
    data/geography/reference_IRIS_geo2024.csv (IRIS inchangés) ou déduits du code commune ;
  - certaines variables sont nommées autrement (période d'achèvement : P17_RP_ACH19 au lieu de P22_RP_ACH1919… ;
    catégories socioprofessionnelles des actifs : C17_ACT1564_CS1-6 en PCS 2003 au lieu des groupes GSEC de la PCS 2020) ;
  - d'autres n'existent pas (combustible principal, indicateur de peuplement, actifs par diplôme…) : elles restent
    vides (NULL) pour ce millésime.
"""
import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

REFERENCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "geography", "reference_IRIS_geo2024.csv")
COG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "geography", "COG_au_01-01-2024.csv")


def aliases(year):
    """Colonne attendue → colonne équivalente des anciens millésimes."""
    yy = str(year)[-2:]
    p = f"P{yy}_"
    last = str(year - 3)[-2:]  # dernière période d'achèvement : 2006 à N-3
    out = {}
    for prefix in ("RP", "RPMAISON", "RPAPPART"):
        out.update({f"{p}{prefix}_ACH1919": f"{p}{prefix}_ACH19", f"{p}{prefix}_ACH1945": f"{p}{prefix}_ACH45",
                    f"{p}{prefix}_ACH1970": f"{p}{prefix}_ACH70", f"{p}{prefix}_ACH1990": f"{p}{prefix}_ACH90",
                    f"{p}{prefix}_ACH2005": f"{p}{prefix}_ACH05", f"{p}{prefix}_ACH20{yy}": f"{p}{prefix}_ACH{last}",
                    f"{p}{prefix}_ACH2019": f"{p}{prefix}_ACH{last}"})
    # catégories socioprofessionnelles : PCS 2003 (CS1-CS6) avant la PCS 2020 (groupes GSEC), mêmes six groupes
    c = f"C{yy}_"
    for i in range(1, 7):
        out[f"{c}ACT1564_STAT_GSEC1{i}_2{i}"] = f"{c}ACT1564_CS{i}"
        out[f"{c}ACTOCC1564_STAT_GSEC1{i}"] = f"{c}ACTOCC1564_CS{i}"
    return out


def _geo():
    ref = pd.read_csv(REFERENCE, sep=";", dtype=str, encoding="utf-8-sig")
    cog = pd.read_csv(COG, sep=";", dtype=str)
    cog["CODGEO"] = cog["CODGEO"].str.zfill(5)
    cog["DEP"] = cog["DEP"].where(cog["DEP"].str.len() > 1, cog["DEP"].str.zfill(2))
    return ref, dict(zip(cog["DEP"], cog["REG"]))


def complete_columns(df, column_map, year):
    """Ajoute à df les colonnes de column_map absentes du fichier (alias, géographie, sinon vides)."""
    df = df.copy()
    missing = [c for c in column_map if c not in df.columns]
    if not missing:
        return df
    al = aliases(year)
    renamed, empty = [], []
    for col in missing:
        if col in ("LIBIRIS", "DEP", "REG"):
            continue
        src = al.get(col)
        if src and src in df.columns:
            df[col] = df[src]
            renamed.append(f"{src}→{col}")
        else:
            df[col] = None
            empty.append(col)
    if any(c in missing for c in ("LIBIRIS", "DEP", "REG")):
        ref, dep_reg = _geo()
        iris = df["IRIS"].astype(str).str.strip().str.zfill(9)
        com = df["COM"].astype(str).str.strip().str.zfill(5)
        names = dict(zip(ref["CODE_IRIS"], ref["LIB_IRIS"]))
        if "LIBIRIS" in missing:
            df["LIBIRIS"] = iris.map(names)
            logger.info(f"   Noms d'IRIS repris du référentiel 2024 : {df['LIBIRIS'].notna().sum():,} / {len(df):,} "
                        f"(IRIS modifiés depuis : nom vide)")
        dep = com.str[:3].where(com.str.startswith("97"), com.str[:2])
        if "DEP" in missing:
            df["DEP"] = dep
        if "REG" in missing:
            df["REG"] = dep.map(dep_reg)
    if renamed:
        logger.info(f"   Colonnes renommées ({year}) : {', '.join(renamed)}")
    if empty:
        logger.warning(f"   ⚠️ {len(empty)} variables absentes du millésime {year}, laissées vides : {', '.join(empty)}")
    return df


def dry_run_summary(df, table):
    """Résumé d'un DataFrame prêt à importer (mode --dry-run)."""
    logger.info(f"🧪 Dry-run {table} : {len(df):,} IRIS, {df['com_code'].nunique():,} communes")
    ref = pd.read_csv(REFERENCE, sep=";", dtype=str, encoding="utf-8-sig")
    unknown = ~df["iris_code"].isin(set(ref["CODE_IRIS"]))
    logger.info(f"   IRIS absents du référentiel 2024 (découpage modifié depuis) : {unknown.sum():,} "
                f"({unknown.mean() * 100:.1f} %)")
    q = df[df["com_code"] == "59484"]
    if not q.empty:
        num = [c for c in df.columns if c not in ("iris_code", "com_code", "iris_name", "dep_code", "reg_code", "year")]
        logger.info(f"   Quiévrechain : {len(q)} IRIS ; " + ", ".join(f"{c}={q[c].sum():,.0f}" for c in num[:4]))
    empty = [c for c in df.columns if df[c].isna().all()]
    if empty:
        logger.info(f"   Colonnes vides : {empty}")
    logger.info("🧪 Rien n'a été écrit en base")
