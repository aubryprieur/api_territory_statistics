"""
Import des indicateurs des établissements scolaires (ministère de l'Éducation nationale, data.education.gouv.fr)
dans trois tables :

  schools_by_year            une ligne par (uai, year) : écoles, collèges, lycées
      - indice de position sociale (IPS) et sa position nationale (décile, centile) parmi les établissements
        du même type la même année (écoles ; collèges ; lycées par type LEGT, LPO, LP), public et privé
      - collèges : résultats au DNB et valeurs ajoutées (taux de réussite, note à l'écrit), accès 6e-3e
      - lycées : résultats au bac général et technologique / professionnel et valeurs ajoutées
      - indice d'éloignement (collèges et lycées, base 100 = moyenne nationale, plus élevé = plus éloigné)
    year = année de rentrée pour l'IPS et l'éloignement (2023 = rentrée 2023-2024), année de session pour
    les examens (2025 = DNB ou bac de juin 2025).

  schools_national_by_year   distribution nationale par (school_type, year, metric) : moyenne, déciles D1-D9

  sixth_grade_age_by_territory  âge à l'entrée en 6e (à l'heure, en avance, en retard) : DEP, REG, FRANCE
      ('FM' = somme des départements de métropole), par sexe et secteur.

Sources (dossier data/education/schools/) :
  fr-en-ips-ecoles-ap2022, fr-en-ips-colleges-ap2023, fr-en-ips-lycees-ap2023
  fr-en-indicateurs-valeur-ajoutee-colleges
  fr-en-indicateurs-de-resultat-des-lycees-gt_v2, fr-en-indicateurs-de-resultat-des-lycees-pro_v2
  fr-en-indice_eloignement_college_ap2022, fr-en-indice_eloignement_lycee_ap2020
  fr-en-age_eleves_entree_sixieme
(L'ancien indice d'éloignement des collèges 2019-2021, sur une autre échelle, n'est pas importé.)

Usage :
    python scripts/import_schools.py --dry-run
    python scripts/import_schools.py
"""
import argparse
import io
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/education/schools"
FIRST_EXAM_YEAR = 2017
LYCEE_TYPES = ("LEGT", "LPO", "LP")

SCHOOL_COLUMNS = [
    "uai", "year", "school_type", "lycee_type", "name", "sector", "commune_code", "commune_name", "department_code",
    # IPS
    "ips", "ips_sd", "ips_gt", "ips_pro", "ips_post_bac", "ips_decile", "ips_percentile",
    "ips_national", "ips_national_public", "ips_national_private", "ips_academic", "ips_departmental",
    "ips_departmental_public", "ips_departmental_private",
    # Indice d'éloignement
    "remoteness", "remoteness_decile", "remoteness_percentile",
    # Collèges : DNB
    "dnb_candidates", "dnb_success_rate", "dnb_success_va", "dnb_written_score", "dnb_written_va",
    "dnb_mentions_rate", "dnb_tb_rate", "access_6_3_rate", "dnb_success_va_percentile", "dnb_written_va_percentile",
    # Lycées : bac général et technologique
    "gt_candidates", "gt_success_rate", "gt_success_va", "gt_access_rate", "gt_access_va",
    "gt_mentions_rate", "gt_mentions_va", "gt_success_va_percentile", "gt_access_va_percentile",
    # Lycées : bac professionnel
    "pro_candidates", "pro_success_rate", "pro_success_va", "pro_access_rate", "pro_access_va",
    "pro_mentions_rate", "pro_mentions_va", "pro_success_va_percentile", "pro_access_va_percentile",
]
TEXT_COLUMNS = {"uai", "school_type", "lycee_type", "name", "sector", "commune_code", "commune_name", "department_code"}
INT_COLUMNS = {"year", "ips_decile", "remoteness_decile"}

NATIONAL_COLUMNS = ["school_type", "year", "metric", "establishments", "mean",
                    "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9"]

SIXTH_COLUMNS = ["geo_level", "geo_code", "year"] + [
    f"{m}_{g}" for g in ("total", "girls", "boys", "public", "private")
    for m in ("pupils", "on_time", "early", "late")]


def _read(d, name):
    return pd.read_parquet(os.path.join(d, f"{name}.parquet"))


def _year(series):
    """'2023-2024' -> 2023 ; date 2025-01-01 -> 2025 ; '2025' -> 2025."""
    return series.astype(str).str[:4].astype(int)


def _num(series):
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def _sector(series):
    s = series.astype(str).str.lower()
    return np.where(s.str.startswith("pu"), "public", np.where(s.str.startswith("pr"), "private", None))


def _rate(part, whole):
    part, whole = _num(part), _num(whole)
    return (part / whole * 100).where(whole > 0).round(1)


# ----------------------------------------------------------------------------- lecture des sources
def load_ips(d):
    e = _read(d, "fr-en-ips-ecoles-ap2022")
    ecoles = pd.DataFrame({
        "uai": e["uai"], "year": _year(e["rentree_scolaire"]), "school_type": "ecole", "lycee_type": None,
        "name": e["nom_de_l_etablissement"], "sector": _sector(e["secteur"]),
        "commune_code": e["code_insee_de_la_commune"], "commune_name": e["nom_de_la_commune"],
        "department_code": e["code_du_departement"],
        "ips": _num(e["ips"]), "ips_national": _num(e["ips_national"]),
        "ips_national_public": _num(e["ips_national_public"]), "ips_national_private": _num(e["ips_national_prive"]),
        "ips_academic": _num(e["ips_academique"]), "ips_departmental": _num(e["ips_departemental"]),
        "ips_departmental_public": _num(e["ips_departemental_public"]),
        "ips_departmental_private": _num(e["ips_departemental_prive"]),
    })
    c = _read(d, "fr-en-ips-colleges-ap2023")
    colleges = pd.DataFrame({
        "uai": c["uai"], "year": _year(c["rentree_scolaire"]), "school_type": "college", "lycee_type": None,
        "name": c["nom_de_l_etablissement"], "sector": _sector(c["secteur"]),
        "commune_code": c["code_insee_de_la_commune"], "commune_name": c["nom_de_la_commune"],
        "department_code": c["code_du_departement"],
        "ips": _num(c["ips"]), "ips_sd": _num(c["ecart_type_de_l_ips"]), "ips_national": _num(c["ips_national"]),
        "ips_national_public": _num(c["ips_national_public"]), "ips_national_private": _num(c["ips_national_prive"]),
        "ips_academic": _num(c["ips_academique"]), "ips_departmental": _num(c["ips_departemental"]),
        "ips_departmental_public": _num(c["ips_departemental_public"]),
        "ips_departmental_private": _num(c["ips_departemental_prive"]),
    })
    l = _read(d, "fr-en-ips-lycees-ap2023")
    lt = l["type_de_lycee"].astype(str).str.upper()

    def by_type(prefix):
        """Valeur de référence du type de lycée (et du secteur) de chaque ligne."""
        out = pd.Series(np.nan, index=l.index)
        for t in LYCEE_TYPES:
            col = f"{prefix}_{t.lower()}"
            if col in l:
                out = out.where(lt != t, _num(l[col]))
        return out

    def by_type_sector(prefix, sector):
        out = pd.Series(np.nan, index=l.index)
        for t in LYCEE_TYPES:
            col = f"{prefix}_{t.lower()}_{sector}"
            if col in l:
                out = out.where(lt != t, _num(l[col]))
        return out

    lycees = pd.DataFrame({
        "uai": l["uai"], "year": _year(l["rentree_scolaire"]), "school_type": "lycee", "lycee_type": lt,
        "name": l["nom_de_l_etablissement"], "sector": _sector(l["secteur"]),
        "commune_code": l["code_insee_de_la_commune"], "commune_name": l["nom_de_la_commune"],
        "department_code": l["code_du_departement"],
        "ips": _num(l["ips_etab"]), "ips_sd": _num(l["ecart_type_etablissement"]),
        "ips_gt": _num(l["ips_voie_gt"]), "ips_pro": _num(l["ips_voie_pro"]), "ips_post_bac": _num(l["ips_post_bac"]),
        "ips_national": by_type("ips_national"),
        "ips_national_public": by_type_sector("ips_national", "public"),
        "ips_national_private": by_type_sector("ips_national", "prive"),
        "ips_academic": by_type("ips_academique"), "ips_departmental": by_type("ips_departemental"),
        "ips_departmental_public": by_type_sector("ips_departemental", "public"),
        "ips_departmental_private": by_type_sector("ips_departemental", "prive"),
    })
    # Quelques établissements figurent dans deux fichiers (école européenne...) : on garde la première ligne
    return pd.concat([ecoles, colleges, lycees], ignore_index=True).drop_duplicates(["uai", "year"])


def load_colleges_exams(d):
    v = _read(d, "fr-en-indicateurs-valeur-ajoutee-colleges")
    return pd.DataFrame({
        "uai": v["uai"], "year": _year(v["session"]), "school_type": "college",
        "name": v["nom_de_l_etablissement"], "sector": _sector(v["secteur"]),
        "commune_name": v["commune"], "department_code": v["code_departement"],
        "dnb_candidates": _num(v["nb_candidats_g"]), "dnb_success_rate": _num(v["taux_de_reussite_g"]),
        "dnb_success_va": _num(v["va_du_taux_de_reussite_g"]), "dnb_written_score": _num(v["note_a_l_ecrit_g"]),
        "dnb_written_va": _num(v["va_de_la_note_g"]),
        "dnb_mentions_rate": _rate(v["nb_mentions_global_g"], v["nb_candidats_g"]),
        "dnb_tb_rate": _rate(v["nb_mentions_tb_g"], v["nb_candidats_g"]),
        "access_6_3_rate": _num(v["taux_d_acces_6eme_3eme"]),
    })


def load_lycees_exams(d):
    frames = []
    for name, p in (("fr-en-indicateurs-de-resultat-des-lycees-gt_v2", "gt"),
                    ("fr-en-indicateurs-de-resultat-des-lycees-pro_v2", "pro")):
        r = _read(d, name)
        r = r[_year(r["annee"]) >= FIRST_EXAM_YEAR]
        frames.append(pd.DataFrame({
            "uai": r["uai"], "year": _year(r["annee"]), "school_type": "lycee",
            "name": r["libelle_uai"], "sector": _sector(r["secteur"]),
            "commune_code": r["code_commune"].astype(str).str.zfill(5), "commune_name": r["libelle_commune"],
            "department_code": r["code_departement"],
            f"{p}_candidates": _num(r["presents_total"]), f"{p}_success_rate": _num(r["taux_reu_total"]),
            f"{p}_success_va": _num(r["va_reu_total"]), f"{p}_access_rate": _num(r["taux_acces_2nde"]),
            f"{p}_access_va": _num(r["va_acces_2nde"]), f"{p}_mentions_rate": _num(r["taux_men_total"]),
            f"{p}_mentions_va": _num(r["va_men_total"]),
        }))
    gt, pro = frames
    key = ["uai", "year"]
    ident = ["school_type", "name", "sector", "commune_code", "commune_name", "department_code"]
    m = gt.merge(pro, on=key, how="outer", suffixes=("", "_pro"))
    for c in ident:
        m[c] = m[c].where(m[c].notna(), m[f"{c}_pro"])
    return m.drop(columns=[f"{c}_pro" for c in ident])


def load_remoteness(d):
    frames = []
    for name, t in (("fr-en-indice_eloignement_college_ap2022", "college"),
                    ("fr-en-indice_eloignement_lycee_ap2020", "lycee")):
        r = _read(d, name)
        frames.append(pd.DataFrame({
            "uai": r["uai"], "year": _year(r["rentree_scolaire"]), "school_type": t,
            "name": r["patronyme"], "department_code": r["code_departement"],
            "remoteness": _num(r["indice_eloignement"]),
        }))
    return pd.concat(frames, ignore_index=True).drop_duplicates(["uai", "year"])


# ----------------------------------------------------------------------------- assemblage
def _rank_group(df):
    """Groupe de comparaison nationale : écoles ; collèges ; lycées par type (LEGT, LPO, LP)."""
    return df["school_type"].where(df["school_type"] != "lycee", "lycee_" + df["lycee_type"].fillna("NA"))


def _percentile(values, groups):
    """Centile (0-100) : part des établissements du groupe ayant une valeur strictement inférieure,
    plus la moitié des ex aequo."""
    return values.groupby(groups).rank(method="average", pct=True).mul(100).round(1).where(values.notna())


def _decile(values, groups):
    """Décile national 1 (valeurs les plus basses) à 10 (les plus hautes)."""
    pct = values.groupby(groups).rank(method="first", pct=True)
    return np.ceil(pct * 10).clip(1, 10).where(values.notna())


def build(d=DIR):
    ips = load_ips(d)
    colleges = load_colleges_exams(d)
    lycees = load_lycees_exams(d)
    remote = load_remoteness(d)

    # Annuaire : identité la plus récente de chaque établissement (fichiers IPS en priorité, ils ont la commune)
    ident_cols = ["school_type", "lycee_type", "name", "sector", "commune_code", "commune_name", "department_code"]
    sources = [ips, lycees, colleges, remote]
    directory = (pd.concat([s.reindex(columns=["uai", "year"] + ident_cols).assign(_rank=i)
                            for i, s in enumerate(sources)], ignore_index=True)
                 .sort_values(["_rank", "year"], ascending=[True, False]))
    directory = directory.groupby("uai").first().drop(columns=["year", "_rank"])  # first() ignore les valeurs nulles

    key = ["uai", "year"]
    data = ips.drop(columns=[c for c in ident_cols if c in ips]).copy()
    for s in (colleges, lycees, remote):
        values = s.drop(columns=[c for c in ident_cols if c in s])
        data = data.merge(values, on=key, how="outer")
    data = data.join(directory, on="uai")

    # Positions nationales, par type d'établissement et par année
    groups = [_rank_group(data), data["year"]]
    data["ips_decile"] = _decile(data["ips"], groups)
    data["ips_percentile"] = _percentile(data["ips"], groups)
    data["remoteness_decile"] = _decile(data["remoteness"], groups)
    data["remoteness_percentile"] = _percentile(data["remoteness"], groups)
    type_groups = [data["school_type"], data["year"]]
    for col in ("dnb_success_va", "dnb_written_va", "gt_success_va", "gt_access_va", "pro_success_va",
                "pro_access_va"):
        data[f"{col}_percentile"] = _percentile(data[col], type_groups)

    for col in SCHOOL_COLUMNS:
        if col not in data:
            data[col] = np.nan
    data = data[SCHOOL_COLUMNS].sort_values(key).reset_index(drop=True)
    data["commune_code"] = data["commune_code"].where(data["commune_code"].astype(str).str.len() == 5)
    return data


def national(data):
    """Distribution nationale de chaque indicateur par groupe de comparaison et par année."""
    metrics = ["ips", "remoteness", "dnb_success_rate", "dnb_success_va", "dnb_written_score", "dnb_written_va",
               "access_6_3_rate", "gt_success_rate", "gt_success_va", "gt_access_rate", "gt_access_va",
               "pro_success_rate", "pro_success_va", "pro_access_rate", "pro_access_va"]
    df = data.assign(group=_rank_group(data))
    rows = []
    for (group, year), g in df.groupby(["group", "year"]):
        for metric in metrics:
            v = g[metric].dropna()
            if len(v) < 10:
                continue
            q = v.quantile([i / 10 for i in range(1, 10)]).round(2).tolist()
            rows.append([group, int(year), metric, len(v), round(v.mean(), 2), *q])
        # Les valeurs ajoutées et résultats des lycées : tous types confondus aussi
    lyc = df[df.school_type == "lycee"]
    for year, g in lyc.groupby("year"):
        for metric in metrics:
            v = g[metric].dropna()
            if len(v) < 10 or metric in ("ips", "remoteness"):
                continue
            q = v.quantile([i / 10 for i in range(1, 10)]).round(2).tolist()
            rows.append(["lycee", int(year), metric, len(v), round(v.mean(), 2), *q])
    return pd.DataFrame(rows, columns=NATIONAL_COLUMNS)


def sixth_grade(d=DIR):
    a = _read(d, "fr-en-age_eleves_entree_sixieme")
    a = a[a["code_departement"].notna()].reset_index(drop=True)  # la ligne « National » (France entière) est écartée
    suffix = {"total": "tot", "girls": "fill", "boys": "gar", "public": "pub", "private": "pr"}
    measure = {"pupils": "eff_{s}", "on_time": "1_a_l_heure_{s}", "early": "2_en_avance_{s}",
               "late": "3_en_retard_{s}"}
    dep = pd.DataFrame({"geo_level": "DEP", "geo_code": a["code_departement"].astype(str).str.strip(),
                        "year": _year(a["annee"])})
    for g, s in suffix.items():
        for m, pattern in measure.items():
            dep[f"{m}_{g}"] = _num(a[pattern.format(s=s)])
    values = [c for c in SIXTH_COLUMNS if c not in ("geo_level", "geo_code", "year")]
    reg_of = a["code_region_insee"].astype(str).str.strip()
    reg = dep.assign(geo_code=reg_of.values).groupby(["geo_code", "year"])[values].sum(min_count=1).reset_index()
    reg["geo_level"] = "REG"
    metro = dep[~dep["geo_code"].str.startswith("97")]
    fm = metro.groupby("year")[values].sum(min_count=1).reset_index()
    fm["geo_level"], fm["geo_code"] = "FRANCE", "FM"
    out = pd.concat([dep, reg, fm], ignore_index=True)
    return out[SIXTH_COLUMNS].sort_values(["geo_level", "geo_code", "year"]).reset_index(drop=True)


# ----------------------------------------------------------------------------- contrôles
def check(data, nat, sixth, commune="59484"):
    logger.info("🔎 Établissements par type et année :")
    tab = data.groupby(["school_type", "year"]).size().unstack(fill_value=0)
    for line in tab.to_string().splitlines():
        logger.info("   " + line)
    logger.info(f"🔎 Lignes sans commune : {data['commune_code'].isna().sum()} "
                f"(établissements absents des fichiers IPS et des résultats des lycées)")
    dup = data.duplicated(["uai", "year"]).sum()
    logger.info(f"🔎 Doublons (uai, année) : {dup}")
    for t in ("ecole", "college"):
        y = data.loc[(data.school_type == t) & data.ips.notna(), "year"].max()
        g = data[(data.school_type == t) & (data.year == y)]
        logger.info(f"🔎 IPS {t}s {y} : moyenne {g.ips.mean():.1f} (référence publiée {g.ips_national.iloc[0]}), "
                    f"effectif par décile {g.ips_decile.value_counts().sort_index().astype(int).tolist()}")
    q = data[data.commune_code == commune]
    logger.info(f"🔎 Commune {commune} :")
    cols = ["uai", "year", "school_type", "name", "ips", "ips_decile", "remoteness", "remoteness_decile",
            "dnb_success_rate", "dnb_success_va", "dnb_success_va_percentile"]
    for line in q[cols].to_string(index=False).splitlines():
        logger.info("   " + line)
    logger.info(f"🔎 Distribution nationale : {len(nat)} lignes ; âge à l'entrée en 6e : {len(sixth)} lignes")
    fm = sixth[sixth.geo_level == "FRANCE"].set_index("year")
    logger.info("🔎 France métropolitaine, élèves en retard à l'entrée en 6e : " +
                ", ".join(f"{y} = {r.late_total / r.pupils_total * 100:.1f} %" for y, r in fm.iterrows()))


# ----------------------------------------------------------------------------- écriture
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
    for c in columns:
        if c in INT_COLUMNS:
            out[c] = out[c].astype("Int64")
    buf = io.StringIO()
    out.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
    buf.seek(0)
    cur.execute(f"DELETE FROM {table}")
    cur.copy_expert(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
    logger.info(f"✅ {table} : {cur.rowcount} lignes importées")


def write(data, nat, sixth):
    for df in (data, nat, sixth):
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].where(df[c].isna(), df[c].astype(str).str.replace("\t", " ").str.replace("\n", " "))
    conn = _connect()
    try:
        with conn.cursor() as cur:
            _copy(cur, "schools_by_year", data, SCHOOL_COLUMNS)
            _copy(cur, "schools_national_by_year", nat, NATIONAL_COLUMNS)
            _copy(cur, "sixth_grade_age_by_territory", sixth, SIXTH_COLUMNS)
        conn.commit()
        conn.autocommit = True
        with conn.cursor() as cur:
            for t in ("schools_by_year", "schools_national_by_year", "sixth_grade_age_by_territory"):
                cur.execute(f"ANALYZE {t}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=DIR, help="dossier des fichiers parquet de l'Éducation nationale")
    parser.add_argument("--dry-run", action="store_true", help="contrôles uniquement, aucune écriture")
    args = parser.parse_args()

    data = build(args.dir)
    nat = national(data)
    sixth = sixth_grade(args.dir)
    check(data, nat, sixth)
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(data, nat, sixth)
        logger.info("🏁 Import terminé")
