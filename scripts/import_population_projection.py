"""
Projections démographiques par commune (méthode des composantes par cohortes, version simplifiée), horizon 10 ans.
Table population_projection (une ligne par commune, résultats en JSONB).

Données (data/population/) :
  - TD_POP1B_2017.CSV, TD_POP1B_2022.csv : population par sexe et âge détaillé (recensements 2017 et 2022, 1er janvier)
  - 7_FM_Table_mortalite_triennale.xlsx (Insee, DEC7) : quotients de mortalité par sexe et âge, France métropolitaine
    (table 2017-2019 pour mesurer les migrations 2017-2022, table la plus récente pour projeter)
  - data/births/DS_ETAT_CIVIL_NAIS_COMMUNES_data.csv : naissances domiciliées 2014-2023
  - population_by_territory (base) : pyramide 2023 par tranche de 5 ans, pour recaler le point de départ

Méthode :
  1. Migrations par âge : la population 2017 est vieillie de 5 ans (mortalité nationale) et complétée des naissances
     2017-2021 ; l'écart avec le recensement 2022 donne le solde migratoire par tranche de 5 ans. Taux annuel par âge,
     rapproché du taux du département pour les petits effectifs (poids = attendu / (attendu + 300)).
  2. Point de départ 1er janvier 2023 : population 2022 vieillie d'un an (naissances 2022 observées), recalée sur la
     pyramide du recensement 2023 par sexe et tranche de 5 ans.
  3. Projection annuelle 2023 → 2033 : vieillissement, décès (table la plus récente), migrations par âge, naissances =
     taux de natalité de la commune (naissances 2021-2023 / femmes de 15-49 ans) x femmes de 15-49 ans projetées
     (naissances 2023 observées).
  Pyramide projetée : effectifs par sexe et tranche de 5 ans en 2033 (scénario tendance).
  Scénarios : tendance ; sans migrations ; natalité basse / haute (± variation annuelle des naissances 2014-2023 de la
  commune, entre 10 % et 35 %).
  Test : taux de natalité 2014-2016 appliqué aux naissances 2017-2023 connues (écart en %).

Usage :
    python scripts/import_population_projection.py --dry-run        # sans base : sans recalage sur la pyramide 2023
    python scripts/import_population_projection.py
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time
import zipfile

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/population"
P17_FILE, P22_FILE = f"{DIR}/TD_POP1B_2017.CSV", f"{DIR}/TD_POP1B_2022.csv"
MORTALITY = f"{DIR}/7_FM_Table_mortalite_triennale.xlsx"
BIRTHS = "data/births/DS_ETAT_CIVIL_NAIS_COMMUNES_data.csv"
BASE, HORIZON = 2023, 2033
YEARS = list(range(BASE, HORIZON + 1))
MAX_AGE = 100
BOY_SHARE = 0.512
SHRINK = 300            # poids du taux communal : attendu / (attendu + SHRINK)
MIG_CAP = 0.12          # taux annuel de migration plafonné à ± 12 % par âge
SPREAD_MIN, SPREAD_MAX = 0.10, 0.35
MIG_GROUPS = [(a, a + 4) for a in range(0, 85, 5)] + [(85, MAX_AGE)]
OUT_GROUPS = {"0_2": (0, 2), "3_5": (3, 5), "6_10": (6, 10), "11_14": (11, 14), "15_17": (15, 17),
              "18_24": (18, 24), "60_74": (60, 74), "75_84": (75, 84), "85p": (85, MAX_AGE), "total": (0, MAX_AGE)}
BIRTH_DEPENDENT = ["0_2", "3_5", "6_10"]   # groupes touchés par les naissances projetées (nés après 2023) d'ici 2033
PYR = [(a, a + 4, f"{a}_{a + 4}") for a in range(0, 95, 5)] + [(95, MAX_AGE, "ge95")]


# ------------------------------------------------------------------------------------------------- lecture
def mortality_tables():
    """Quotients de mortalité {année de la table: array[2 sexes, 101 âges]} (xlsx « strict » lu en XML)."""
    z = zipfile.ZipFile(MORTALITY)
    wb = z.read("xl/workbook.xml").decode()
    names = dict(re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wb))
    relx = z.read("xl/_rels/workbook.xml.rels").decode()
    rels = {i: t for t, i in re.findall(r'Target="([^"]+)"[^>]*Id="([^"]+)"', relx)}
    rels.update(dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', relx)))

    def read(sheet):
        x = z.read("xl/" + rels[names[sheet]].split("xl/")[-1]).decode()
        q = np.full((2, MAX_AGE + 1), np.nan)
        for r in re.findall(r"<row[^>]*>(.*?)</row>", x, re.S):
            cells = dict(re.findall(r'<c r="([A-Z]+)\d+"[^>]*>\s*<v>([^<]*)</v>', r))
            a = cells.get("A")
            if a and a.isdigit() and int(a) <= MAX_AGE and "F" in cells and "I" in cells:
                q[0, int(a)] = float(cells["I"]) / 1e5   # hommes
                q[1, int(a)] = float(cells["F"]) / 1e5   # femmes
        q = pd.DataFrame(q).T.ffill().T.values           # âges non publiés : dernier quotient connu
        return np.clip(q, 0, 1)

    sheets = sorted(int(s) for s in names if s.isdigit())
    est = "2019" if "2019" in names else str(sheets[0])
    latest = str(sheets[-1])
    logger.info(f"📖 Mortalité : table {est} (estimation des migrations), table {latest} (projection)")
    return read(est), read(latest), latest


def read_population(path):
    d = pd.read_csv(path, sep=";", dtype={"CODGEO": str, "AGED100": str}, usecols=["NIVGEO", "CODGEO", "SEXE", "AGED100", "NB"])
    d = d[d.NIVGEO == "COM"]
    d["age"] = d.AGED100.astype(int).clip(upper=MAX_AGE)
    d["s"] = d.SEXE.astype(int) - 1
    p = d.groupby(["CODGEO", "s", "age"]).NB.sum()
    logger.info(f"📖 {path} : {p.index.get_level_values(0).nunique():,} communes, {p.sum():,.0f} habitants")
    return p


def to_array(p, codes):
    idx = pd.MultiIndex.from_product([codes, [0, 1], range(MAX_AGE + 1)])
    return p.reindex(idx).fillna(0).values.reshape(len(codes), 2, MAX_AGE + 1)


def read_births(codes):
    b = pd.read_csv(BIRTHS, sep=";", dtype={"GEO": str})
    b = b[b.GEO_OBJECT == "COM"].pivot_table(index="GEO", columns="TIME_PERIOD", values="OBS_VALUE", aggfunc="sum")
    logger.info(f"📖 Naissances {b.columns.min()}-{b.columns.max()} : {len(b):,} communes")
    return b.reindex(codes)


def read_pyramid_2023(conn, codes):
    cols = ", ".join(f"pyr_{s}_{g}" for s in ("men", "women") for _, _, g in PYR)
    d = pd.read_sql(f"SELECT geo_code, {cols} FROM population_by_territory WHERE geo_level = 'COM' AND year = {BASE}", conn)
    d = d.set_index("geo_code").reindex(codes)
    arr = np.stack([d[[f"pyr_{s}_{g}" for _, _, g in PYR]].values for s in ("men", "women")], axis=1)
    logger.info(f"📖 Pyramide {BASE} : {d.notna().any(axis=1).sum():,} communes")
    return arr  # [N, 2, groupes]


# ------------------------------------------------------------------------------------------------- calcul
def survival(q):
    return 1 - q   # [2, 101]


def age_one_year(pop, s, births, mig=None):
    """Vieillit d'un an : décès, naissances de l'année (âge 0 au 1er janvier suivant), migrations par âge."""
    new = np.zeros_like(pop)
    new[:, :, 1:] = pop[:, :, :-1] * s[None, :, :-1]
    new[:, :, MAX_AGE] += pop[:, :, MAX_AGE] * s[None, :, MAX_AGE]
    half = 1 - (1 - s[:, 0]) / 2   # naissances réparties dans l'année
    new[:, 0, 0] = births * BOY_SHARE * half[0]
    new[:, 1, 0] = births * (1 - BOY_SHARE) * half[1]
    if mig is not None:
        new *= (1 + mig)[:, None, :]
    return new


def migration_rates(p17, p22, births, q_est, dep):
    """Taux annuel de migration par âge [N, 101], estimé sur 2017 → 2022 (rapproché du département)."""
    s = survival(q_est)
    exp = p17.copy()
    for _ in range(5):                          # 5 vieillissements sans naissances ni migrations
        exp = age_one_year(exp, s, np.zeros(len(exp)))
    for k, y in enumerate(range(2017, 2022)):   # naissances 2017-2021 -> âges 4..0 au 1er janvier 2022
        age = 2021 - y
        b = births[y].fillna(0).values if y in births else 0
        surv_b = np.prod(s[:, :age + 1], axis=1) if age >= 0 else 1
        exp[:, 0, age] += b * BOY_SHARE * surv_b[0]
        exp[:, 1, age] += b * (1 - BOY_SHARE) * surv_b[1]
    known = p17.sum(axis=(1, 2)) > 0            # commune présente en 2017 (sinon : taux du département)
    rates = np.zeros((len(p17), MAX_AGE + 1))
    df_dep = pd.Series(dep)
    for lo, hi in MIG_GROUPS:
        o = p22[:, :, lo:hi + 1].sum(axis=(1, 2))
        e = exp[:, :, lo:hi + 1].sum(axis=(1, 2))
        o_dep = pd.Series(np.where(known, o, 0)).groupby(df_dep).transform("sum").values
        e_dep = pd.Series(np.where(known, e, 0)).groupby(df_dep).transform("sum").values
        r_dep = np.where(e_dep > 0, o_dep / np.where(e_dep > 0, e_dep, 1) - 1, 0)
        r_com = np.where(e > 0, o / np.where(e > 0, e, 1) - 1, r_dep)
        w = np.where(known, e / (e + SHRINK), 0)
        r5 = np.clip(w * r_com + (1 - w) * r_dep, -0.95, 3)
        annual = np.clip((1 + r5) ** (1 / 5) - 1, -MIG_CAP, MIG_CAP)
        rates[:, lo:hi + 1] = annual[:, None]
    return rates, known


def build(conn=None):
    t0 = time.time()
    q_est, q_proj, table = mortality_tables()
    p17s, p22s = read_population(P17_FILE), read_population(P22_FILE)
    codes = sorted(p22s.index.get_level_values(0).unique())
    p17, p22 = to_array(p17s, codes), to_array(p22s, codes)
    births = read_births(codes)
    dep = [c[:3] if c.startswith("97") else c[:2] for c in codes]

    mig, known = migration_rates(p17, p22, births, q_est, dep)
    s = survival(q_proj)

    # Natalité : naissances 2021-2023 / femmes de 15-49 ans (2022) ; département à défaut
    w22 = p22[:, 1, 15:50].sum(axis=1)
    b_recent = births.reindex(columns=[2021, 2022, 2023]).mean(axis=1).values
    f = np.where(w22 > 0, b_recent / np.where(w22 > 0, w22, 1), np.nan)
    f_dep = pd.Series(np.nan_to_num(b_recent)).groupby(dep).transform("sum").values / \
        np.maximum(pd.Series(w22).groupby(dep).transform("sum").values, 1)
    f = np.where(np.isfinite(f), f, f_dep)
    b_all = births.reindex(columns=range(2014, 2024))
    mean_b = b_all.mean(axis=1).values
    spread = np.where(mean_b >= 5, b_all.std(axis=1).values / np.maximum(mean_b, 1e-9), SPREAD_MAX)
    spread = np.clip(np.nan_to_num(spread, nan=SPREAD_MAX), SPREAD_MIN, SPREAD_MAX)
    # Test : taux 2014-2016 appliqué aux femmes 2017-2022 (interpolées) -> naissances 2017-2023 connues
    w17 = p17[:, 1, 15:50].sum(axis=1)
    f_old = births.reindex(columns=[2014, 2015, 2016]).mean(axis=1).values / np.where(w17 > 0, w17, np.nan)
    pred = sum(f_old * (w17 + (w22 - w17) * (y - 2017) / 5) for y in range(2017, 2024))
    obs = b_all.reindex(columns=range(2017, 2024)).sum(axis=1, min_count=7).values
    test_err = np.where((obs > 0) & np.isfinite(pred), 100 * (pred / np.where(obs > 0, obs, 1) - 1), np.nan)

    # Point de départ : 1er janvier 2023 (naissances 2022 observées), recalé sur la pyramide 2023
    b22 = births[2022].fillna(0).values if 2022 in births else f * w22
    pop0 = age_one_year(p22, s, b22, mig)
    if conn is not None:
        pyr = read_pyramid_2023(conn, codes)
        for gi, (lo, hi, _) in enumerate(PYR):
            proj = pop0[:, :, lo:hi + 1].sum(axis=2)
            ratio = np.where((proj > 0) & np.isfinite(pyr[:, :, gi]), pyr[:, :, gi] / np.where(proj > 0, proj, 1), 1)
            pop0[:, :, lo:hi + 1] *= np.clip(ratio, 0.5, 2)[:, :, None]
    else:
        logger.info("   Sans base : point de départ 2023 non recalé sur la pyramide du recensement 2023")

    b23 = births[2023].values if 2023 in births else np.full(len(codes), np.nan)
    scenarios = {"trend": (mig, f), "no_migration": (None, f), "low": (mig, f * (1 - spread)), "high": (mig, f * (1 + spread))}
    out = {}
    for name, (m, fert) in scenarios.items():
        pop = pop0.copy()
        series = {g: [pop[:, :, lo:hi + 1].sum(axis=(1, 2))] for g, (lo, hi) in OUT_GROUPS.items()}
        bser = []
        for y in YEARS[:-1]:
            bb = np.where(np.isfinite(b23), b23, fert * pop[:, 1, 15:50].sum(axis=1)) if y == BASE else \
                fert * pop[:, 1, 15:50].sum(axis=1)
            bser.append(bb)
            pop = age_one_year(pop, s, bb, m)
            for g, (lo, hi) in OUT_GROUPS.items():
                series[g].append(pop[:, :, lo:hi + 1].sum(axis=(1, 2)))
        out[name] = ({g: np.stack(v, axis=1) for g, v in series.items()}, np.stack(bser, axis=1))
        if name == "trend":   # pyramide projetée à l'horizon : effectifs par sexe et tranche de 5 ans
            pyr_end = np.stack([pop[:, :, lo:hi + 1].sum(axis=2) for lo, hi, _ in PYR], axis=2)  # [N, 2, groupes]
    logger.info(f"🔢 Projections calculées pour {len(codes):,} communes ({time.time() - t0:.0f} s)")

    rows = []
    for i, c in enumerate(codes):
        rint = lambda a: [int(round(float(v))) for v in a]
        trend, tb = out["trend"]
        data = {
            "base_year": BASE, "years": YEARS, "mortality_table": table,
            "groups": {g: rint(trend[g][i]) for g in OUT_GROUPS},
            "no_migration": {g: rint(out["no_migration"][0][g][i]) for g in OUT_GROUPS},
            "low": {g: rint(out["low"][0][g][i]) for g in BIRTH_DEPENDENT},
            "high": {g: rint(out["high"][0][g][i]) for g in BIRTH_DEPENDENT},
            "births": {"years": YEARS[:-1], "trend": [round(float(v), 1) for v in tb[i]],
                       "low": [round(float(v), 1) for v in out["low"][1][i]],
                       "high": [round(float(v), 1) for v in out["high"][1][i]],
                       "no_migration": [round(float(v), 1) for v in out["no_migration"][1][i]],
                       "observed": {int(y): (None if pd.isna(v) else int(v)) for y, v in b_all.iloc[i].items()}},
            "fertility_per_1000_women": round(float(f[i]) * 1000, 1) if np.isfinite(f[i]) else None,
            "births_spread_pct": round(float(spread[i]) * 100),
            "births_test_error_pct": None if not np.isfinite(test_err[i]) else round(float(test_err[i]), 1),
            "migration_source": "commune" if known[i] else "département",
            "migration_annual_pct": {f"{lo}_{hi}": round(float(mig[i, lo]) * 100, 2) for lo, hi in MIG_GROUPS},
            "pyramid": {"year": HORIZON, "groups": [g for _, _, g in PYR],
                        "men": rint(pyr_end[i, 0]), "women": rint(pyr_end[i, 1])},
        }
        rows.append({"geo_code": c, "population_2023": round(float(pop0[i].sum())), "data": json.dumps(data, separators=(",", ":"))})
    return pd.DataFrame(rows)


def check(df):
    logger.info(f"🔎 {len(df):,} communes ; taille JSON moyenne {df.data.str.len().mean():,.0f} caractères "
                f"(total {df.data.str.len().sum() / 1e6:,.0f} Mo)")
    for code in ("59484", "91376", "01004", "75056"):
        r = df[df.geo_code == code]
        if r.empty:
            continue
        d = json.loads(r.iloc[0].data)
        g = d["groups"]
        logger.info(f"🔎 {code} : population {g['total'][0]} -> {g['total'][5]} (2028) -> {g['total'][10]} (2033) ; "
                    f"natalité {d['fertility_per_1000_women']} ‰ ± {d['births_spread_pct']} % ; test naissances "
                    f"{d['births_test_error_pct']} %")
        for k in ("0_2", "3_5", "6_10", "11_14", "15_17", "18_24", "60_74", "75_84", "85p"):
            lo = d["low"].get(k, [None] * 11)[10]
            hi = d["high"].get(k, [None] * 11)[10]
            logger.info(f"      {k:<6} {g[k][0]:>7} -> {g[k][5]:>7} -> {g[k][10]:>7}  (sans migr. {d['no_migration'][k][10]:>7}"
                        + (f", fourchette {lo}-{hi}" if lo is not None else "") + ")")
        logger.info(f"      naissances/an : observées 2021-2023 {[d['births']['observed'].get(str(y)) or d['births']['observed'].get(y) for y in (2021, 2022, 2023)]}, "
                    f"projetées 2028 {d['births']['trend'][5]} ({d['births']['low'][5]}-{d['births']['high'][5]})")


def _connect():
    import psycopg2
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(conn, df):
    buf = io.StringIO()
    for r in df.itertuples(index=False):
        data = r.data.replace("\\", "\\\\")
        buf.write(f"{r.geo_code}\t{BASE}\t{r.population_2023}\t{data}\n")
    buf.seek(0)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM population_projection")
            cur.copy_expert("COPY population_projection (geo_code, base_year, population, data) FROM STDIN WITH (FORMAT text)", buf)
            logger.info(f"✅ {cur.rowcount:,} communes importées")
            cur.execute("SELECT count(*) FROM population_projection")
            logger.info(f"🔎 Contrôle : {cur.fetchone()[0]:,} lignes en base")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche le contrôle sans écrire")
    args = parser.parse_args()
    conn = _connect() if os.environ.get("DATABASE_URL") else None
    try:
        df = build(conn)
        check(df)
        if args.dry_run or conn is None:
            logger.info("🧪 Dry-run : rien n'a été écrit en base")
        else:
            write(conn, df)
            logger.info("🏁 Import terminé")
    finally:
        if conn:
            conn.close()
