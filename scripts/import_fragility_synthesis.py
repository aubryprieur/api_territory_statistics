"""
Synthèse des fragilités : pour chaque commune et chacun des 38 indicateurs du catalogue (app/fragility_catalog.py),
valeur, effectif, rang parmi toutes les communes et rang parmi les communes de même densité (grille de densité INSEE à
7 niveaux, data/geography/grille_densite_2025.xlsx). Tables fragility_synthesis et fragility_reference.

Les valeurs sont lues dans les tables déjà en base, avec les mêmes calculs que les services de l'API (year_data) ;
quelques indicateurs sont calculés ici (RSA, prime d'activité et ARS rapportés au recensement 2023, demandeurs d'emploi
pour 100 actifs, part des 75 ans ou plus) ; les 20-24 ans « ni seuls ni en couple » viennent de la base Couples -
Familles - Ménages 2022 (data/families/commune/base-cc-coupl-fam-men-2022.CSV).

Millésime : pour chaque indicateur, le plus récent couvrant au moins la moitié des communes du meilleur millésime.
Rang (0 à 100) : position de la commune parmi les communes ayant une valeur, orientée pour que 100 = plus touchée
(plus élevé pour les indicateurs « up », plus faible pour les « down ») ; une commune compte pour une.

Usage (DATABASE_URL de Heroku exporté) :
    python scripts/import_fragility_synthesis.py --dry-run
    python scripts/import_fragility_synthesis.py
"""
import argparse
import io
import json
import logging
import os
import sys
import time

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.fragility_catalog import INDICATORS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DENSITY = "data/geography/grille_densite_2025.xlsx"
CFM = "data/families/commune/base-cc-coupl-fam-men-2022.CSV"
CENSUS_YEAR = 2023
LEVELS = ("COM", "FRANCE")


# ------------------------------------------------------------------------------------------------- lecture
def load_rows(session, model, fn, fields, last_years=3):
    """Lignes COM et FRANCE des derniers millésimes d'une table, passées dans la fonction de calcul du service."""
    years = sorted(y for (y,) in session.query(model.year).filter(model.geo_level == "COM").distinct())[-last_years:]
    t0 = time.time()
    recs = []
    q = (session.query(model).filter(model.geo_level.in_(LEVELS), model.year.in_(years))
         .yield_per(5000))
    for r in q:
        d = fn(r)
        recs.append({"geo_level": r.geo_level, "geo_code": r.geo_code, "year": r.year,
                     **{f: d.get(f) for f in fields}})
    df = pd.DataFrame(recs)
    logger.info(f"📖 {model.__tablename__} : {len(df):,} lignes, millésimes {years} ({time.time() - t0:.0f} s)")
    return df


def fields_for(source):
    out = []
    for i in INDICATORS:
        if i["source"] == source:
            out += [i["field"]] + ([i["count"]] if i["count"] else [])
    return list(dict.fromkeys(out))


def load_sources(session):
    from app import models as m
    from app.services.revenues_service import RevenuesService
    from app.services.tax_households_service import TaxHouseholdsService
    from app.services.fragilities_service import FragilitiesService
    from app.services.employment_activity_service import EmploymentActivityService
    from app.services.education_training_service import EducationTrainingService
    from app.services.sdg_indicators_service import SdgIndicatorsService
    from app.services.sports_service import SportsService
    from app.services.childcare_offer_service import ChildcareOfferService
    from app.services.senior_fragilities_service import SeniorFragilitiesService
    from app.services.elderly_care_service import ElderlyCareService
    from app.services.housing_service import HousingService
    from app.services.delinquency_service import DelinquencyService
    from app.services.caf_benefits_service import CafBenefitsService
    from app.services.job_seekers_service import JobSeekersService
    from app.services.family_service import FamilyService
    from app.services.household_service import HouseholdService

    generic = {
        "revenues": RevenuesService(), "tax_households": TaxHouseholdsService(), "fragilities": FragilitiesService(),
        "employment": EmploymentActivityService(), "education": EducationTrainingService(),
        "sdg": SdgIndicatorsService(), "sports": SportsService(), "childcare": ChildcareOfferService(),
        "senior_fragilities": SeniorFragilitiesService(), "elderly_care": ElderlyCareService(),
        "housing": HousingService(), "delinquency": DelinquencyService(),
    }
    src = {}
    for name, svc in generic.items():
        last = 10 if name == "sdg" else 3
        src[name] = load_rows(session, svc.MODEL, svc.year_data, fields_for(name), last_years=last)
    src["family"] = load_rows(session, m.FamilyByTerritory, FamilyService()._year_data, fields_for("family"))
    src["household"] = load_rows(session, m.HouseholdByTerritory, HouseholdService()._year_data,
                                 fields_for("household"))

    # Population : 75 ans ou plus (pop_ge80 + 75-79 ans) et population totale (dénominateurs)
    pop = pd.read_sql(
        f"""SELECT geo_level, geo_code, year, pop,
                   pop_ge80 + COALESCE(pyr_men_75_79, 0) + COALESCE(pyr_women_75_79, 0) AS pop_75p
            FROM population_by_territory WHERE geo_level IN ('COM', 'FRANCE') AND year = {CENSUS_YEAR}""",
        session.bind)
    pop["age_75p_share"] = (100 * pop.pop_75p / pop["pop"]).where(pop["pop"] > 0).round(2)
    src["population"] = pop
    logger.info(f"📖 population_by_territory {CENSUS_YEAR} : {len(pop):,} lignes")

    # CAF : RSA, prime d'activité (population couverte / population), ARS (foyers / familles avec enfants)
    caf_svc = CafBenefitsService()
    caf = load_rows(session, caf_svc.MODEL, caf_svc.year_data, ["rsa_persons", "ppa_persons", "ars_households"])
    ft = m.FamilyByTerritory.__tablename__
    fam = pd.read_sql(
        f"""SELECT geo_level, geo_code, total_families - families_0_children AS families_with_children
            FROM {ft} WHERE geo_level IN ('COM', 'FRANCE')
              AND year = (SELECT max(year) FROM {ft} WHERE year <= {CENSUS_YEAR})""", session.bind)
    caf = (caf.merge(pop[["geo_level", "geo_code", "pop"]], on=["geo_level", "geo_code"], how="left")
           .merge(fam, on=["geo_level", "geo_code"], how="left"))
    caf["rsa_population_rate"] = (100 * caf.rsa_persons / caf["pop"]).where(caf["pop"] > 0).round(2)
    caf["ppa_population_rate"] = (100 * caf.ppa_persons / caf["pop"]).where(caf["pop"] > 0).round(2)
    caf["ars_families_rate"] = (100 * caf.ars_households / caf.families_with_children).where(
        caf.families_with_children > 0).round(2)
    src["caf"] = caf

    # Demandeurs d'emploi ABC pour 100 actifs de 15-64 ans (même millésime que le recensement)
    js_svc = JobSeekersService()
    js = load_rows(session, js_svc.MODEL, js_svc.year_data, ["abc"], last_years=6)
    act = pd.read_sql(
        f"""SELECT geo_level, geo_code, year, active_15_64 FROM {m.EmploymentByTerritory.__tablename__}
            WHERE geo_level IN ('COM', 'FRANCE')""", session.bind)
    js = js.merge(act, on=["geo_level", "geo_code", "year"], how="inner")
    js["job_seekers_rate"] = (100 * js.abc / js.active_15_64).where(js.active_15_64 > 0).round(2)
    src["job_seekers"] = js

    # 20-24 ans ni seuls ni en couple (base Couples - Familles - Ménages 2022)
    c = pd.read_csv(CFM, sep=";", dtype={"CODGEO": str},
                    usecols=["CODGEO", "P22_POPMEN2024", "P22_POP2024_PSEUL", "P22_POP2024_COUPLE"])
    c["young_with_parents"] = c.P22_POPMEN2024 - c.P22_POP2024_PSEUL - c.P22_POP2024_COUPLE
    tot = c[["P22_POPMEN2024", "young_with_parents"]].sum()
    c = pd.concat([c.assign(geo_level="COM").rename(columns={"CODGEO": "geo_code"}),
                   pd.DataFrame([{"geo_level": "FRANCE", "geo_code": "FM", **tot.to_dict()}])], ignore_index=True)
    c["young_with_parents_share"] = (100 * c.young_with_parents / c.P22_POPMEN2024).where(
        c.P22_POPMEN2024 > 0).round(2)
    c["year"] = 2022
    src["cfm"] = c
    logger.info(f"📖 {CFM} : {len(c):,} lignes")
    return src, pop


# ------------------------------------------------------------------------------------------------- calcul
def pick_year(df, field):
    com = df[(df.geo_level == "COM") & df[field].notna()]
    if com.empty:
        return None
    cov = com.groupby("year").size()
    ok = cov[cov >= cov.max() / 2]
    return int(ok.index.max())


def rank(series, direction):
    s = series if direction == "up" else -series
    return ((s.rank(method="average") - 0.5) / s.notna().sum() * 100).round(1)


def build(src, pop, density):
    com_pop = pop[pop.geo_level == "COM"].set_index("geo_code")["pop"]
    base = density.copy()
    per_commune, refs = {}, []
    for ind in INDICATORS:
        df = src[ind["source"]]
        field = ind["field"]
        if field not in df.columns:
            logger.warning(f"   ⚠️ {ind['key']} : champ {field} absent de la source {ind['source']}")
            continue
        year = pick_year(df, field)
        if year is None:
            logger.warning(f"   ⚠️ {ind['key']} : aucune valeur communale")
            continue
        d = df[df.year == year]
        com = d[d.geo_level == "COM"].drop_duplicates("geo_code").set_index("geo_code")
        values = pd.to_numeric(com[field], errors="coerce").dropna()
        counts = pd.to_numeric(com[ind["count"]], errors="coerce") if ind["count"] and ind["count"] in com else None
        fr = d[d.geo_level == "FRANCE"]
        france_value = float(fr[field].iloc[0]) if not fr.empty and pd.notna(fr[field].iloc[0]) else None

        frame = pd.DataFrame({"v": values}).join(base[["dens7"]], how="left")
        frame["p_fr"] = rank(frame.v, ind["direction"])
        frame["p_dens"] = frame.groupby("dens7")["v"].transform(lambda s: rank(s, ind["direction"]))
        q = 0.8 if ind["direction"] == "up" else 0.2
        refs.append({"indicator": ind["key"], "scope": "FR", "year": year, "n": len(frame),
                     "median": round(frame.v.median(), 2), "alert_value": round(frame.v.quantile(q), 2),
                     "france_value": france_value})
        for dens, g in frame.dropna(subset=["dens7"]).groupby("dens7"):
            refs.append({"indicator": ind["key"], "scope": dens, "year": year, "n": len(g),
                         "median": round(g.v.median(), 2), "alert_value": round(g.v.quantile(q), 2),
                         "france_value": None})
        for code, r in frame.iterrows():
            cnt = counts.get(code) if counts is not None else None
            per_commune.setdefault(code, {})[ind["key"]] = [
                round(float(r.v), 2), None if cnt is None or pd.isna(cnt) else round(float(cnt)),
                float(r.p_fr), None if pd.isna(r.p_dens) else float(r.p_dens)]
        logger.info(f"   {ind['key']:<30} {year}  {len(frame):>6,} communes  France {france_value}")
    rows = []
    for code, data in per_commune.items():
        dens = base.loc[code] if code in base.index else None
        rows.append({"geo_code": code,
                     "dens7": None if dens is None else dens.dens7,
                     "dens7_label": None if dens is None else dens.dens7_label,
                     "population": None if code not in com_pop.index or pd.isna(com_pop.get(code)) else float(com_pop.get(code)),
                     "data": json.dumps(data, separators=(",", ":"))})
    return pd.DataFrame(rows), pd.DataFrame(refs)


def read_density():
    d = pd.read_excel(DENSITY, sheet_name="Maille communale", header=4, dtype=str)
    d = d.rename(columns={"CODGEO": "geo_code", "DENS7": "dens7", "LIBDENS7": "dens7_label"})
    logger.info(f"📖 Grille de densité : {len(d):,} communes")
    return d.set_index("geo_code")[["dens7", "dens7_label"]]


def check(syn, ref):
    logger.info(f"🔎 {len(syn):,} communes, {ref.indicator.nunique()} indicateurs ; sans catégorie de densité : "
                f"{syn.dens7.isna().sum()}")
    q = syn[syn.geo_code == "59484"]
    if not q.empty:
        r = q.iloc[0]
        logger.info(f"🔎 59484 {r.dens7_label} ({r.population}) :")
        for k, v in json.loads(r.data).items():
            logger.info(f"     {k:<30} valeur {v[0]:>9}  effectif {v[1]}  rang France {v[2]:>5}  rang densité {v[3]}")


def _connect():
    import psycopg2
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(conn, syn, ref):
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fragility_synthesis")
            cur.execute("DELETE FROM fragility_reference")
            buf = io.StringIO()
            syn[["geo_code", "dens7", "dens7_label", "population", "data"]].to_csv(
                buf, sep="\t", header=False, index=False, na_rep="\\N", quoting=3, escapechar="\\")
            buf.seek(0)
            cur.copy_expert("COPY fragility_synthesis (geo_code, dens7, dens7_label, population, data) "
                            "FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ fragility_synthesis : {cur.rowcount:,} lignes")
            cols = ["indicator", "scope", "year", "n", "median", "alert_value", "france_value"]
            buf = io.StringIO()
            ref[cols].to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
            buf.seek(0)
            cur.copy_expert(f"COPY fragility_reference ({', '.join(cols)}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
                            buf)
            logger.info(f"✅ fragility_reference : {cur.rowcount:,} lignes")
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM fragility_synthesis")
            logger.info(f"🔎 Contrôle après écriture : {cur.fetchone()[0]:,} communes en base")
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche le contrôle sans écrire")
    args = parser.parse_args()
    from app.database import SessionLocal
    session = SessionLocal()
    try:
        src, pop = load_sources(session)
        syn, ref = build(src, pop, read_density())
        check(syn, ref)
        if args.dry_run:
            logger.info("🧪 Dry-run : rien n'a été écrit en base")
        else:
            session.close()
            conn = _connect()
            try:
                write(conn, syn, ref)
            finally:
                conn.close()
            logger.info("🏁 Import terminé")
    finally:
        session.close()
