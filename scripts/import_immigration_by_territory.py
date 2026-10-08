"""
Import immigrés et étrangers (INSEE, recensement 2023) dans immigration_by_territory, à toutes les échelles :
    COM, ARM, EPCI, DEP, REG, FRANCE ('FM' = France métropolitaine)

Sources (data/immigration/, fichiers « DS_RP_TD_… » du recensement 2023) :
  - DS_RP_TD_IMMI_AGESEXEMPSTA_PRINC_2023 : population selon le statut d'immigré (IMMI 1 = immigré, 0 = non immigré),
    l'âge, le sexe et la situation d'activité (EMPSTA_ENQ : 1 emploi, 2 chômage, 31 retraite, 33 études,
    35 au foyer, 36 autres inactifs)
  - DS_RP_TD_NAT_AGESEX_PRINC_2023        : population selon la nationalité (100 = étrangers, 250 = Français)
  - DS_RP_TD_NAT_AGESEXEMPSTA_PRINC_2023  : 15 ans ou plus selon la nationalité et la situation d'activité
  - DS_RP_TD_IMMI_AGESEXPCS_COMP_2023     : 15 ans ou plus selon le statut d'immigré et la catégorie
    socioprofessionnelle (exploitation complémentaire)
Un immigré est une personne née étrangère à l'étranger et résidant en France ; un étranger est une personne qui
n'a pas la nationalité française (une partie des immigrés est devenue française, une partie des étrangers est née
en France).

Usage :
    python scripts/import_immigration_by_territory.py --dry-run
    python scripts/import_immigration_by_territory.py
"""
import argparse
import io
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/immigration"
YEAR = 2023
LEVELS = ["COM", "ARM", "EPCI", "DEP", "REG", "FRANCE"]
KEY = ["geo_level", "geo_code", "year"]
FILES = {
    "immi": "DS_RP_TD_IMMI_AGESEXEMPSTA_PRINC_2023.parquet",
    "nat": "DS_RP_TD_NAT_AGESEX_PRINC_2023.parquet",
    "nat_act": "DS_RP_TD_NAT_AGESEXEMPSTA_PRINC_2023.parquet",
    "pcs": "DS_RP_TD_IMMI_AGESEXPCS_COMP_2023.parquet",
}
ACTIVITY = {"1": "employed", "2": "unemployed", "31": "retired", "33": "students", "35": "homemakers",
            "36": "other_inactive"}
AGES = {"Y_LT15": "lt15", "Y15T24": "15_24", "Y25T54": "25_54", "Y_GE55": "ge55"}

# colonne -> (fichier, filtres) ; les dimensions non citées sont prises au total « _T »
SPECS = {}
for grp, immi in (("imm", "1"), ("nonimm", "0")):
    SPECS[f"{grp}"] = ("immi", {"IMMI": immi, "AGE": "_T"})
    SPECS[f"{grp}_women"] = ("immi", {"IMMI": immi, "AGE": "_T", "SEX": "F"})
    for age, a in AGES.items():
        SPECS[f"{grp}_{a}"] = ("immi", {"IMMI": immi, "AGE": age})
    for code, name in ACTIVITY.items():
        SPECS[f"{grp}_{name}_15p"] = ("immi", {"IMMI": immi, "AGE": "Y_GE15", "EMPSTA_ENQ": code})
    SPECS[f"{grp}_employed_25_54"] = ("immi", {"IMMI": immi, "AGE": "Y25T54", "EMPSTA_ENQ": "1"})
    SPECS[f"{grp}_women_25_54"] = ("immi", {"IMMI": immi, "AGE": "Y25T54", "SEX": "F"})
    SPECS[f"{grp}_women_employed_25_54"] = ("immi", {"IMMI": immi, "AGE": "Y25T54", "SEX": "F", "EMPSTA_ENQ": "1"})
    SPECS[f"{grp}_women_homemakers_25_54"] = ("immi", {"IMMI": immi, "AGE": "Y25T54", "SEX": "F",
                                                        "EMPSTA_ENQ": "35"})
    for pcs in "123456":
        SPECS[f"{grp}_pcs{pcs}"] = ("pcs", {"IMMI": immi, "AGE": "Y_GE15", "PCS": pcs})
SPECS["population"] = ("immi", {"IMMI": "_T", "AGE": "_T"})
for grp, nat in (("foreign", "100"), ("french", "250")):
    SPECS[grp] = ("nat", {"NATIONALITY_TYPE": nat, "AGE": "_T"})
    SPECS[f"{grp}_women"] = ("nat", {"NATIONALITY_TYPE": nat, "AGE": "_T", "SEX": "F"})
    SPECS[f"{grp}_lt15"] = ("nat", {"NATIONALITY_TYPE": nat, "AGE": "Y_LT15"})
    SPECS[f"{grp}_employed_15p"] = ("nat_act", {"NATIONALITY_TYPE": nat, "AGE": "Y_GE15", "EMPSTA_ENQ": "1"})
    SPECS[f"{grp}_unemployed_15p"] = ("nat_act", {"NATIONALITY_TYPE": nat, "AGE": "Y_GE15", "EMPSTA_ENQ": "2"})
MEASURES = list(SPECS)
COLUMNS = KEY + MEASURES
DIMENSIONS = {"immi": ["AGE", "SEX", "IMMI", "EMPSTA_ENQ"], "nat": ["AGE", "SEX", "NATIONALITY_TYPE"],
              "nat_act": ["AGE", "SEX", "NATIONALITY_TYPE", "EMPSTA_ENQ"], "pcs": ["AGE", "SEX", "IMMI", "PCS"]}


def _read(d, name):
    path = os.path.join(d, FILES[name])
    df = pd.read_parquet(path, columns=["GEO", "GEO_OBJECT", *DIMENSIONS[name], "OBS_VALUE"],
                         filters=[("GEO_OBJECT", "in", LEVELS)])
    for c in ["GEO", "GEO_OBJECT", *DIMENSIONS[name]]:
        df[c] = df[c].astype("category")  # comparaisons rapides sur des millions de lignes
    df = df[(df["GEO_OBJECT"] != "FRANCE") | (df["GEO"] == "FM")]
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return df


def load(d=DIR):
    frames = {name: _read(d, name) for name in FILES}
    out = None
    for col, (name, filters) in SPECS.items():
        df = frames[name]
        mask = pd.Series(True, index=df.index)
        for dim in DIMENSIONS[name]:
            mask &= df[dim] == filters.get(dim, "_T")
        s = df[mask].groupby(["GEO_OBJECT", "GEO"], observed=True)["OBS_VALUE"].sum(min_count=1).rename(col)
        out = s.to_frame() if out is None else out.join(s, how="outer")
        if s.empty:
            raise ValueError(f"Aucune valeur pour {col} : vérifier les filtres {filters}")
    out = out.reset_index().rename(columns={"GEO_OBJECT": "geo_level", "GEO": "geo_code"})
    out["geo_level"] = out["geo_level"].astype(str)
    out["geo_code"] = out["geo_code"].astype(str)
    out["year"] = YEAR
    out[MEASURES] = out[MEASURES].round(2)
    return out[COLUMNS].sort_values(KEY).reset_index(drop=True)


def check(data):
    logger.info("🔎 Territoires par niveau : " + str(data.groupby("geo_level").size().to_dict()))
    gap = (data["imm"] + data["nonimm"] - data["population"]).abs().max()
    logger.info(f"🔎 Immigrés + non-immigrés - population : écart max {gap:.2f}")
    gap = (data["foreign"] + data["french"] - data["population"]).abs().max()
    logger.info(f"🔎 Étrangers + Français - population : écart max {gap:.2f}")
    com = data[data.geo_level.isin(["COM", "ARM"])].copy()
    com["dep"] = com.geo_code.str[:3].where(com.geo_code.str.startswith("97"), com.geo_code.str[:2])
    dep = data[data.geo_level == "DEP"].set_index("geo_code")
    sums = com.groupby("dep")["imm"].sum()
    rel = ((dep["imm"] - sums.reindex(dep.index)).abs() / dep["imm"]).dropna()
    logger.info(f"🔎 Immigrés : écart relatif médian département vs somme des communes = {rel.median():.3%}")
    for level, code in (("COM", "59484"), ("DEP", "59"), ("FRANCE", "FM")):
        r = data[(data.geo_level == level) & (data.geo_code == code)]
        if r.empty:
            continue
        r = r.iloc[0]
        ue = lambda g: r[f"{g}_unemployed_15p"] / (r[f"{g}_employed_15p"] + r[f"{g}_unemployed_15p"]) * 100
        logger.info(f"🔎 {level} {code} : population {r.population:,.0f}, immigrés {r.imm / r.population:.1%}, "
                    f"étrangers {r.foreign / r.population:.1%}, chômage immigrés {ue('imm'):.1f} % / "
                    f"non-immigrés {ue('nonimm'):.1f} %, emploi des immigrées 25-54 ans "
                    f"{r.imm_women_employed_25_54 / r.imm_women_25_54:.1%}")


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
    buf = io.StringIO()
    data.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM immigration_by_territory WHERE year = %s", (YEAR,))
            logger.info(f"🗑️ {cur.rowcount} lignes supprimées pour {YEAR}")
            # noms entre guillemets : « foreign » est un mot réservé de PostgreSQL
            columns = ", ".join('"%s"' % c for c in COLUMNS)
            cur.copy_expert(
                f"COPY immigration_by_territory ({columns}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ {cur.rowcount} lignes importées")
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE immigration_by_territory")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des fichiers parquet du recensement")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = load(args.dir)
    check(data)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data)
        logger.info("🏁 Import terminé")
