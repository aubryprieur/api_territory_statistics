"""
Services publics locaux de l'Annuaire de l'administration (DILA — Base de données locales de Service-Public.fr) pour
les cartes de localisation du tableau de bord : mairies, France services, CCAS, CAF, CPAM, Carsat, MSA, missions
locales, France Travail, points-justice, PMI, MDPH… (types DILA_TYPES de app/services/equipment_points_service.py).
Écrits dans equipment_points avec typequ = « DILA:<code pivot> » (year = 2026) ; les lignes BPE ne sont pas touchées.

Source (data/equipment/annuaire/) : export JSON de data.gouv.fr (*data.gouv_local.json : {"service": [...]}).
Chaque service : nom, pivot[].type_service_local, code_insee_commune, adresse[] (longitude, latitude en WGS84).
Paris, Lyon, Marseille : le code commune est ramené à l'arrondissement (code postal), comme la BPE.
EPCI et nom de commune : repris de la BPE (data/equipment/bpe25_slim.parquet).

Compléments facultatifs (antennes ou permanences absentes de l'annuaire, ex. une antenne de mission locale) :
data/equipment/annuaire/complements.csv, séparateur « ; », colonnes type;nom;code_commune;latitude;longitude
(type = code pivot de l'annuaire : mission_locale, caf, france_services…).

Mise à jour : télécharger le nouvel export, puis (DATABASE_URL de Heroku exporté)
    python scripts/import_annuaire_points.py --dry-run
    python scripts/import_annuaire_points.py
et augmenter Api::EquipmentPointsService::DATA_VERSION côté Rails.
"""
import argparse
import glob
import io
import json
import logging
import os
import re
import sys

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.equipment_points_service import DILA_TYPES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIR = "data/equipment/annuaire"
BPE = "data/equipment/bpe25_slim.parquet"
YEAR = 2026
PLM = {"75056": ("75", "751"), "69123": ("6900", "6938"), "13055": ("130", "132")}  # code commune -> (préfixe CP, préfixe arr.)


def source_file():
    files = sorted(glob.glob(os.path.join(DIR, "*data.gouv_local.json")))
    if not files:
        raise FileNotFoundError(f"Export JSON de l'annuaire introuvable dans {DIR}")
    return files[-1]


def location(service):
    """Adresse géolocalisée : l'adresse physique d'abord, sinon toute adresse avec des coordonnées."""
    addrs = [a for a in service.get("adresse") or [] if a.get("latitude") and a.get("longitude")]
    addrs.sort(key=lambda a: a.get("type_adresse") != "Adresse")
    for a in addrs:
        try:
            lat, lon = float(a["latitude"]), float(a["longitude"])
        except (TypeError, ValueError):
            continue
        if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat, lon) != (0, 0):
            return lat, lon, a
    return None


def depcom(code, addr):
    code = (code or "").strip()
    if code in PLM:
        cp = re.sub(r"\D", "", (addr or {}).get("code_postal") or "")
        if code == "75056" and re.fullmatch(r"75(0\d|1\d|20)\d", cp) and 1 <= int(cp[3:]) <= 20:
            return f"751{int(cp[3:]):02d}"
        if code == "69123" and re.fullmatch(r"6900\d", cp) and 1 <= int(cp[4]) <= 9:
            return f"6938{cp[4]}"
        if code == "13055" and re.fullmatch(r"130\d\d", cp) and 1 <= int(cp[3:]) <= 16:
            return f"132{int(cp[3:]):02d}"
    return code


def build():
    path = source_file()
    with open(path, encoding="utf-8") as f:
        services = json.load(f)["service"]
    logger.info(f"📖 {path} : {len(services):,} services")
    wanted = {t.split(":", 1)[1] for t in DILA_TYPES}
    rows, no_loc = [], 0
    for s in services:
        types = sorted({p.get("type_service_local") for p in s.get("pivot") or []} & wanted)
        if not types:
            continue
        loc = location(s)
        if loc is None:
            no_loc += 1
            continue
        lat, lon, addr = loc
        code = depcom(s.get("code_insee_commune"), addr)
        if not re.fullmatch(r"\d[\dAB]\d{3}", code or ""):
            no_loc += 1
            continue
        name = re.sub(r"\s+", " ", (s.get("nom") or "")).strip() or None
        for t in types:
            rows.append({"typequ": f"DILA:{t}", "depcom": code, "name": name, "lat": round(lat, 6), "lon": round(lon, 6),
                         "addr_commune": addr.get("nom_commune")})
    extra = os.path.join(DIR, "complements.csv")
    if os.path.exists(extra):
        c = pd.read_csv(extra, sep=";", dtype=str).dropna(subset=["type", "code_commune", "latitude", "longitude"])
        for r in c.itertuples():
            rows.append({"typequ": f"DILA:{r.type.strip()}", "depcom": r.code_commune.strip().zfill(5), "name": r.nom,
                         "lat": round(float(r.latitude.replace(",", ".")), 6),
                         "lon": round(float(r.longitude.replace(",", ".")), 6), "addr_commune": None})
        logger.info(f"➕ {extra} : {len(c)} services ajoutés")
        unknown = set(c.type.str.strip()) - wanted
        if unknown:
            logger.warning(f"⚠️  types absents des groupes de carte (non affichés) : {sorted(unknown)}")
    out = pd.DataFrame(rows).drop_duplicates(subset=["typequ", "name", "lat", "lon"])
    bpe = (pd.read_parquet(BPE, columns=["DEPCOM", "EPCI", "LIBCOM"]).drop_duplicates("DEPCOM")
           .assign(DEPCOM=lambda d: d.DEPCOM.astype(str).str.zfill(5)).set_index("DEPCOM"))
    epci = bpe.EPCI.where(bpe.EPCI.notna() & ~bpe.EPCI.isin(["ZZZZZZZZZ", ""]), None)
    out["epci"] = out.depcom.map(epci)
    out["commune_name"] = out.depcom.map(bpe.LIBCOM.str.title()).fillna(out.addr_commune)
    out["year"], out["qpv"], out["quality"] = YEAR, None, None
    logger.info(f"🔢 {len(out):,} services géolocalisés ({no_loc:,} sans coordonnées ou sans commune) ; "
                f"sans EPCI : {int(out.epci.isna().sum()):,}")
    logger.info(f"   par type : {out.typequ.value_counts().to_dict()}")
    v = out[out.depcom == "76681"]
    logger.info(f"🔎 Sotteville-lès-Rouen (76681) : {len(v)} services : {v[['typequ', 'name']].to_dict('records')}")
    return out


def _connect():
    import psycopg2
    from app.database import engine
    url = engine.url
    params = dict(host=url.host, port=url.port or 5432, dbname=url.database, user=url.username, password=url.password)
    if url.host not in (None, "localhost", "127.0.0.1"):
        params["sslmode"] = "require"
    return psycopg2.connect(**params)


def write(out):
    conn = _connect()
    cols = ["year", "typequ", "depcom", "epci", "commune_name", "name", "lat", "lon", "qpv", "quality"]
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM equipment_points WHERE typequ LIKE 'DILA:%%'")
            logger.info(f"🗑  {cur.rowcount:,} anciens services de l'annuaire supprimés")
            buf = io.StringIO()
            o = out[cols].copy()
            for c in ("commune_name", "name"):
                o[c] = (o[c].astype("string").str.replace("\t", " ", regex=False).str.replace("\n", " ", regex=False)
                        .str.replace("\\", "/", regex=False))
            o.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
            buf.seek(0)
            cur.copy_expert(f"COPY equipment_points ({', '.join(cols)}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
            logger.info(f"✅ equipment_points : {cur.rowcount:,} services de l'annuaire")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="calcule et affiche le contrôle sans écrire")
    args = parser.parse_args()
    out = build()
    if args.dry_run:
        logger.info("🧪 Dry-run : rien n'a été écrit en base")
    else:
        write(out)
        logger.info("🏁 Import terminé")
