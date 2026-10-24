"""
Conversion des bases infracommunales 2023 de l'Insee (nouveau format « Chiffres détaillés », mise en ligne le
15/10/2026 : base_ic_*_2023.xlsx, colonnes nommées en clair, onglets IRIS_2023 et COM_2023_non_irisees) vers l'ancien
format à codes de variables (P23_POP, C23_FAM…), pour réutiliser tels quels les scripts import_iris_*.py.

Choix du format : les classeurs base_ic_*.xlsx reprennent exactement le contenu des anciennes bases IRIS (une ligne par
IRIS, une colonne par variable) ; les fichiers DS_RP_*_IRIS_2023 (parquet / CSV Melodi) sont au format long (une ligne
par croisement) et demanderaient de reconstruire chaque variable.

Écarts avec 2022, gérés ici :
  - population : tranches « moins de 2 ans » et « 2-5 ans » au lieu de 0-2 et 3-5 ans → rangées dans pop_0_2 et
    pop_3_5 (la part des moins de 18 ans reste exacte ; ces deux tranches ne sont pas comparables à 2022) ;
    pop_11_17 = 11-14 + 15-17 ans ;
  - activité : CDD, intérim, emplois aidés et apprentissage regroupés en « autres contrats » (→ P23_SAL15P_CDD,
    les trois autres restent vides) ; détail des non-salariés absent ;
  - communes non découpées en IRIS (onglet COM_2023_non_irisees) : code IRIS = code commune + « 0000 », comme avant.
Géographie au 1er janvier 2025.

Usage :
    python scripts/convert_iris_2023.py --src "<dossier contenant base_ic_*_2023*.xlsx ou .zip>"
    → data/iris/2023/base-ic-{population,familles,logement,formation,activite}-2023.csv
"""
import argparse
import glob
import logging
import os
import unicodedata
import zipfile

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT = "data/iris/2023"
GEO = {"Code géographique": "IRIS", "Libellé géographique": "LIBIRIS", "Type d'Iris": "TYP_IRIS"}

FILES = {
    "population": ("base_ic_population_2023", {
        "Population (princ)": "P23_POP", "Pop Moins de 2 ans (princ)": "P23_POP0002", "Pop 2-5 ans (princ)": "P23_POP0305",
        "Pop 6-10 ans (princ)": "P23_POP0610", "Pop 18-24 ans (princ)": "P23_POP1824", "Pop 25-39 ans (princ)": "P23_POP2539",
        "Pop 40-54 ans (princ)": "P23_POP4054", "Pop 55-64 ans (princ)": "P23_POP5564", "Pop 65-79 ans (princ)": "P23_POP6579",
        "Pop 80 ans ou plus (princ)": "P23_POP80P", "Pop Etrangers (princ)": "P23_POP_ETR", "Pop Immigrés (princ)": "P23_POP_IMM",
        "Pop Femmes (princ)": "P23_POPF", "Pop Hommes (princ)": "P23_POPH",
    }, {"P23_POP1117": ["Pop 11-14 ans (princ)", "Pop 15-17 ans (princ)"]}),
    "familles": ("base_ic_couples_familles_menages_2023", {
        "Pop 15 ans ou plus (princ)": "P23_POP15P", "Pop 15-24 ans (princ)": "P23_POP1524", "Pop 25-54 ans (princ)": "P23_POP2554",
        "Pop 55-79 ans (princ)": "P23_POP5579", "Pop 80 ans ou plus (princ)": "P23_POP80P",
        "Pop 15 ans ou plus vivant seule (princ)": "P23_POP15P_PSEUL", "Pop 15-24 ans vivant seule (princ)": "P23_POP1524_PSEUL",
        "Pop 25-54 ans vivant seule (princ)": "P23_POP2554_PSEUL", "Pop 55-79 ans vivant seule (princ)": "P23_POP5579_PSEUL",
        "Pop 80 ans ou plus vivant seule (princ)": "P23_POP80P_PSEUL", "Familles (compl)": "C23_FAM",
        "Fam Couple avec enfant(s) (compl)": "C23_COUPAENF", "Fam Monoparentales (compl)": "C23_FAMMONO",
        "Fam Couple sans enfant (compl)": "C23_COUPSENF", "Fam 0 enfant moins 25 ans (compl)": "C23_NE24F0",
        "Fam 1 enfant moins 25 ans (compl)": "C23_NE24F1", "Fam 2 enfants moins 25 ans (compl)": "C23_NE24F2",
        "Fam 3 enfants moins 25 ans (compl)": "C23_NE24F3", "Fam 4 enfants ou plus moins 25 ans (compl)": "C23_NE24F4P",
    }, {}),
    "logement": ("base_ic_logement_2023", {
        "Logements (princ)": "P23_LOG", "Résid principales (princ)": "P23_RP",
        "Résid secondaires et logts occasionnels (princ)": "P23_RSECOCC", "Logements vacants (princ)": "P23_LOGVAC",
        "Maisons (princ)": "P23_MAISON", "Appartements (princ)": "P23_APPART", "Résid princ 1 pièce (princ)": "P23_RP_1P",
        "Résid princ 2 pièces (princ)": "P23_RP_2P", "Résid princ 3 pièces (princ)": "P23_RP_3P",
        "Résid princ 4 pièces (princ)": "P23_RP_4P", "Résid princ 5 pièces ou plus (princ)": "P23_RP_5PP",
        "Rés princ de moins de 30 m2 (princ)": "P23_RP_M30M2", "Rés princ de 30 à moins de 40 m2 (princ)": "P23_RP_3040M2",
        "Rés princ de 40 à moins de 60 m2 (princ)": "P23_RP_4060M2", "Rés princ de 60 à moins de 80 m2 (princ)": "P23_RP_6080M2",
        "Rés princ de 80 à moins de 100 m2 (princ)": "P23_RP_80100M2",
        "Rés princ de 100 à moins de 120 m2 (princ)": "P23_RP_100120M2", "Rés princ de 120 m2 ou plus (princ)": "P23_RP_120M2P",
        "Résid princ avt 1919 (princ)": "P23_RP_ACH1919", "Résid princ 1919 à 1945 (princ)": "P23_RP_ACH1945",
        "Résid princ 1946 à 1970 (princ)": "P23_RP_ACH1970", "Résid princ 1971 à 1990 (princ)": "P23_RP_ACH1990",
        "Résid princ 1991 à 2005 (princ)": "P23_RP_ACH2005", "Résid princ 2006 à 2020 (princ)": "P23_RP_ACH2019",
        "Ménages (princ)": "P23_MEN", "Ménages emménagés moins 2 ans (princ)": "P23_MEN_ANEM0002",
        "Ménages emménagés entre 2-4 ans (princ)": "P23_MEN_ANEM0204", "Ménages emménagés entre 5-9 ans (princ)": "P23_MEN_ANEM0509",
        "Ménages emménagés depuis 10 ans ou plus (princ)": "P23_MEN_ANEM10P",
        "Résid princ occupées Propriétaires (princ)": "P23_RP_PROP", "Résid princ occupées Locataires (princ)": "P23_RP_LOC",
        "Résid princ HLM louée vide (princ)": "P23_RP_LOCHLMV", "Résid princ logé gratuit (princ)": "P23_RP_GRAT",
        "Résid princ combustible principal chauffage gaz de ville - Réseau de chaleur (princ)": "P23_RP_CGAZV",
        "Résid princ combustible principal chauffage fioul (princ)": "P23_RP_CFIOUL",
        "Résid princ combustible principal chauffage électicité (princ)": "P23_RP_CELEC",
        "Résid princ combustible principal chauffage gaz en bouteilles ou citerne (princ)": "P23_RP_CGAZB",
        "Résid princ combustible principal chauffage autres (princ)": "P23_RP_CAUT",
        "Ménages au moins une voiture (princ)": "P23_RP_VOIT1P", "Ménages une voiture (princ)": "P23_RP_VOIT1",
        "Ménages deux voitures ou plus (princ)": "P23_RP_VOIT2P", "Résid princ occupation norme (comp)": "C23_RP_NORME",
        "Résid princ sous-occupation modérée (comp)": "C23_RP_SOUSOCC_MOD",
        "Résid princ sous-occupation accentuée (comp)": "C23_RP_SOUSOCC_ACC",
        "Résid princ sous-occupation très accentuée (comp)": "C23_RP_SOUSOCC_TACC",
        "Résid princ suroccupation modérée (comp)": "C23_RP_SUROCC_MOD",
        "Résid princ suroccupation accentuée (comp)": "C23_RP_SUROCC_ACC",
    }, {}),
    "formation": ("base_ic_formation_2023", {
        "Pop 2-5 ans (princ)": "P23_POP0205", "Pop 6-10 ans (princ)": "P23_POP0610", "Pop 11-14 ans (princ)": "P23_POP1114",
        "Pop 15-17 ans (princ)": "P23_POP1517", "Pop 18-24 ans (princ)": "P23_POP1824", "Pop 25-29 ans (princ)": "P23_POP2529",
        "Pop 30 ans ou plus (princ)": "P23_POP30P", "Pop scolarisée 2-5 ans (princ)": "P23_SCOL0205",
        "Pop scolarisée 6-10 ans (princ)": "P23_SCOL0610", "Pop scolarisée 11-14 ans (princ)": "P23_SCOL1114",
        "Pop scolarisée 15-17 ans (princ)": "P23_SCOL1517", "Pop scolarisée 18-24 ans (princ)": "P23_SCOL1824",
        "Pop scolarisée 25-29 ans (princ)": "P23_SCOL2529", "Pop scolarisée 30 ans ou plus (princ)": "P23_SCOL30P",
        "Pop 15 ans ou plus non scolarisée (princ)": "P23_NSCOL15P",
        "Hommes 15 ans ou plus non scolarisés (princ)": "P23_HNSCOL15P",
        "Femmes 15 ans ou plus non scolarisées (princ)": "P23_FNSCOL15P",
    }, {}),
    "activite": ("base_ic_activite_residents_2023", {
        "Pop 15-64 ans (princ)": "P23_POP1564", "Pop 15-24 ans (princ)": "P23_POP1524", "Pop 25-54 ans (princ)": "P23_POP2554",
        "Pop 55-64 ans (princ)": "P23_POP5564", "Inactifs 15-64 ans (princ)": "P23_INACT1564",
        "Inactifs 15-64 ans Hommes (princ)": "P23_HINACT1564", "Inactifs 15-64 ans Femmes (princ)": "P23_FINACT1564",
        "Elèv. Etud. Stag. non rémunérés 15-64 ans (princ)": "P23_ETUD1564",
        "Elèv. Etud. Stag. non rémunérés 15-64 ans Hommes (princ)": "P23_HETUD1564",
        "Elèv. Etud. Stag. non rémunérés 15-64 ans Femmes (princ)": "P23_FETUD1564",
        "Retraités Préretraités 15-64 ans (princ)": "P23_RETR1564", "Retraités Préretraités 15-64 ans Hommes (princ)": "P23_HRETR1564",
        "Retraités Préretraités 15-64 ans Femmes (princ)": "P23_FRETR1564", "Autres inactifs 15-64 ans (princ)": "P23_AINACT1564",
        "Autres inactifs 15-64 ans Hommes (princ)": "P23_HAINACT1564", "Autres inactifs 15-64 ans Femmes (princ)": "P23_FAINACT1564",
        "Actifs 15-64 ans Agriculteurs exploitants (compl)": "C23_ACT1564_STAT_GSEC11_21",
        "Actifs 15-64 ans Artisans, Comm., Chefs entr. (compl)": "C23_ACT1564_STAT_GSEC12_22",
        "Actifs 15-64 ans Cadres, Prof. intel. sup. (compl)": "C23_ACT1564_STAT_GSEC13_23",
        "Actifs 15-64 ans Prof. intermédiaires (compl)": "C23_ACT1564_STAT_GSEC14_24",
        "Actifs 15-64 ans Employés (compl)": "C23_ACT1564_STAT_GSEC15_25",
        "Actifs 15-64 ans Ouvriers (compl)": "C23_ACT1564_STAT_GSEC16_26",
        "Actifs occ 15-64 ans Agriculteurs exploitants (compl)": "C23_ACTOCC1564_STAT_GSEC11",
        "Actifs occ 15-64 ans Artisans, Comm., Chefs entr. (compl)": "C23_ACTOCC1564_STAT_GSEC12",
        "Actifs occ 15-64 ans Cadres Prof. intel. sup. (compl)": "C23_ACTOCC1564_STAT_GSEC13",
        "Actifs occ 15-64 ans Prof. intermédiaires (compl)": "C23_ACTOCC1564_STAT_GSEC14",
        "Actifs occupés 15-64 ans Employés (compl)": "C23_ACTOCC1564_STAT_GSEC15",
        "Actifs occupés 15-64 ans Ouvriers (compl)": "C23_ACTOCC1564_STAT_GSEC16",
        "Actifs occupés 15 ans ou plus (princ)": "P23_ACTOCC15P", "Actifs occupés 15 ans ou plus Hommes (princ)": "P23_HACTOCC15P",
        "Actifs occupés 15 ans ou plus Femmes (princ)": "P23_FACTOCC15P", "Salariés 15 ans ou plus (princ)": "P23_SAL15P",
        "Salariés 15 ans ou plus Hommes (princ)": "P23_HSAL15P", "Salariés 15 ans ou plus Femmes (princ)": "P23_FSAL15P",
        "Non-salariés 15 ans ou plus (princ)": "P23_NSAL15P", "Non-salariés 15 ans ou plus Hommes (princ)": "P23_HNSAL15P",
        "Non-salariés 15 ans ou plus Femmes (princ)": "P23_FNSAL15P", "Actifs occ 15 ans ou plus TP (princ)": "P23_ACTOCC15P_TP",
        "Salariés 15 ans ou plus TP (princ)": "P23_SAL15P_TP", "Salariés 15 ans ou plus TP Hommes (princ)": "P23_HSAL15P_TP",
        "Salariés 15 ans ou plus TP Femmes (princ)": "P23_FSAL15P_TP", "Non-salariés 15 ans ou plus TP (princ)": "P23_NSAL15P_TP",
        "Salariés 15 ans ou plus CDI ou fonctionnaire (princ)": "P23_SAL15P_CDI",
        "Salariés 15 ans ou plus Autres contrats (CDD, intérim, stage, etc.) (princ)": "P23_SAL15P_CDD",
        "Actifs occ 15 ans ou plus travaillent commune résidence (princ)": "P23_ACTOCC15P_ILT1",
        "Actifs occ 15 ans ou plus travaillent autre commune que commune résidence (princ)": "P23_ACTOCC15P_ILT2P",
        "Actifs occ 15 ans ou plus travaillent autre dépt même région résidence (princ)": "P23_ACTOCC15P_ILT3",
        "Actifs occ 15 ans ou plus travaillent autre région en métropole (princ)": "P23_ACTOCC15P_ILT4",
        "Actifs occ 15 ans ou plus travaillent autre région hors métropole (princ)": "P23_ACTOCC15P_ILT5",
        "Actifs occ 15 ans ou plus pas de transport pour travail (princ)": "C23_ACTOCC15P_PAS",
        "Actifs occ 15 ans ou plus marche à pied pour travail (princ)": "C23_ACTOCC15P_MAR",
        "Actifs occ 15 ans ou plus vélo (princ)": "C23_ACTOCC15P_VELO",
        "Actifs occ 15 ans ou plus deux-roues motorisé (princ)": "C23_ACTOCC15P_2ROUESMOT",
        "Actifs occ 15 ans ou plus voiture (princ)": "C23_ACTOCC15P_VOIT",
        "Actifs occ 15 ans ou plus transport en commun (princ)": "C23_ACTOCC15P_TCOM",
    }, {}),
}

# Variables à motif régulier : diplômes (formation), actifs / chômeurs / actifs occupés par âge et sexe (activité)
DIPLOMAS = {"Sans diplôme ou CEP": "DIPLMIN", "BEPC, brevet des collèges, DNB": "BEPC", "CAP-BEP ou équiv.": "CAPBEP",
            "Bac, brevet pro. ou équiv.": "BAC", "Enseignement sup de niveau bac + 2": "SUP2",
            "Enseignement sup de niveau bac + 3 ou 4": "SUP34", "Enseignement sup de niveau bac + 5 ou plus": "SUP5"}
AGES = {"15-64": "1564", "15-24": "1524", "25-54": "2554", "55-64": "5564"}


def norm(s):
    return " ".join(unicodedata.normalize("NFC", str(s)).replace("\xa0", " ").split())


def pattern_map(theme):
    m = {}
    if theme == "formation":
        for lbl, code in DIPLOMAS.items():
            m[f"Pop 15 ans ou plus non scol. {lbl} (princ)"] = f"P23_NSCOL15P_{code}"
            m[f"Hommes 15 ans ou plus non scol. {lbl} (princ)"] = f"P23_HNSCOL15P_{code}"
            m[f"Femmes 15 ans ou plus non scol. {lbl} (princ)"] = f"P23_FNSCOL15P_{code}"
    if theme == "activite":
        for a, code in AGES.items():
            m[f"Pop {a} ans Hommes (princ)"] = f"P23_H{code}"
            m[f"Pop {a} ans Femmes (princ)"] = f"P23_F{code}"
            m[f"Actifs {a} ans (princ)"] = f"P23_ACT{code}"
            m[f"Actifs {a} ans Hommes (princ)"] = f"P23_HACT{code}"
            m[f"Actifs {a} ans Femmes (princ)"] = f"P23_FACT{code}"
            m[f"Actifs occupés {a} ans (princ)"] = f"P23_ACTOCC{code}"
            m[f"Actifs occupés {a} ans Hommes (princ)"] = f"P23_HACTOCC{code}"
            m[f"Actifs occupés {a} ans Femmes (princ)"] = f"P23_FACTOCC{code}"
            m[f"Chômeurs {a} ans (princ)"] = f"P23_CHOM{code}"
            m[f"Chômeurs de {a} ans (princ)"] = f"P23_CHOM{code}"
        for lbl, code in DIPLOMAS.items():
            m[f"Chômeurs {lbl} (princ)"] = f"P23_CHOM_{code}"
            m[f"Actifs {lbl} (princ)"] = f"P23_ACT_{code}"
    return m


def find_source(src, stem):
    for pat in (f"{stem}*.xlsx", f"{stem}*.zip"):
        hits = sorted(glob.glob(os.path.join(src, pat)))
        if hits:
            path = hits[0]
            if path.endswith(".zip"):
                os.makedirs(os.path.join(OUT, "_xlsx"), exist_ok=True)
                with zipfile.ZipFile(path) as z:
                    name = [n for n in z.namelist() if n.endswith(".xlsx")][0]
                    z.extract(name, os.path.join(OUT, "_xlsx"))
                    path = os.path.join(OUT, "_xlsx", name)
            return path
    raise SystemExit(f"Fichier introuvable pour {stem} dans {src}")


def convert(theme, path, mapping, sums):
    mapping = {norm(k): v for k, v in {**mapping, **pattern_map(theme)}.items()}
    frames = []
    for sheet in ("IRIS_2023", "COM_2023_non_irisees"):
        df = pd.read_excel(path, sheet_name=sheet, dtype=str, engine="openpyxl")
        df.columns = [norm(c) for c in df.columns]
        cols = {code: df[col] for col, code in GEO.items() if col in df.columns}
        if sheet == "COM_2023_non_irisees":
            cols["IRIS"] = df["Code géographique"].str.strip().str.zfill(5) + "0000"
        cols.update({code: df[col] for col, code in mapping.items() if col in df.columns})
        cols.update({code: sum(pd.to_numeric(df[norm(c)], errors="coerce").fillna(0) for c in cs)
                     for code, cs in sums.items()})
        out = pd.DataFrame(cols)
        out["IRIS"] = out["IRIS"].str.strip().str.zfill(9)
        out["COM"] = out["IRIS"].str[:5]
        frames.append(out)
        logger.info(f"   {theme} / {sheet} : {len(df):,} lignes")
    res = pd.concat(frames, ignore_index=True)
    missing = sorted(set(mapping.values()) - set(res.columns))
    unmapped = [c for c in df.columns if c not in mapping and c not in GEO and c not in
                ("Libellé de la commune d'appartenance", "Label de l'Iris", "TRIRIS")]
    if missing:
        logger.warning(f"   ⚠️ {theme} : libellés attendus absents du fichier : {missing}")
    logger.info(f"   {theme} : {len(res):,} IRIS et communes, {len(res.columns)} colonnes ; "
                f"{len(unmapped)} colonnes Insee non utilisées")
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", required=True, help="dossier des base_ic_*_2023 (.xlsx ou .zip)")
    parser.add_argument("--only", help="un seul thème : population, familles, logement, formation, activite")
    args = parser.parse_args()
    os.makedirs(OUT, exist_ok=True)
    names = {"population": "evol-struct-pop", "familles": "couples-familles-menages", "logement": "logement",
             "formation": "diplomes-formation", "activite": "activite-residents"}
    for theme, (stem, mapping, sums) in FILES.items():
        if args.only and theme != args.only:
            continue
        path = find_source(args.src, stem)
        logger.info(f"📂 {theme} : {path}")
        res = convert(theme, path, mapping, sums)
        dest = os.path.join(OUT, f"base-ic-{names[theme]}-2023.csv")
        res.to_csv(dest, sep=";", index=False)
        q = res[res.COM == "59484"]
        logger.info(f"✅ {dest} ; Quiévrechain : {len(q)} IRIS, {list(q.IRIS)}")
