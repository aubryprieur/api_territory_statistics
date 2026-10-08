"""
Établissements scolaires — ministère de l'Éducation nationale (data.education.gouv.fr), tables schools_by_year,
schools_national_by_year et sixth_grade_age_by_territory (scripts/import_schools.py).

SchoolsService : écoles, collèges et lycées d'une commune ou d'un EPCI, avec pour chacun
  - l'indice de position sociale (IPS) et sa position parmi les établissements du même type en France
    (décile 1 = 10 % des établissements les plus défavorisés, centile), les IPS de référence (France, académie,
    département, public / privé)
  - collèges : DNB (taux de réussite, note à l'écrit) et valeurs ajoutées, accès de la 6e à la 3e
  - lycées : bac général et technologique / professionnel et valeurs ajoutées
  - l'indice d'éloignement (collèges, lycées ; base 100, plus élevé = plus éloigné des ressources)
et la distribution nationale (moyenne, déciles) de chaque indicateur.

SixthGradeService : élèves en retard / en avance à l'entrée en 6e (départements, régions, France métropolitaine).
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import GeoCode, SchoolByYear, SchoolNationalByYear, SixthGradeAgeByTerritory
from app.services.territory_stats_service import TerritoryStatsService, num, pct

IDENTITY = ["school_type", "lycee_type", "name", "sector", "commune_code", "commune_name", "department_code"]
DECILES = [f"d{i}" for i in range(1, 10)]
TYPE_ORDER = {"ecole": 0, "college": 1, "lycee": 2}
SOURCE = "Ministère de l'Éducation nationale, DEPP — data.education.gouv.fr"
DEFINITIONS = {
    "ips": "Indice de position sociale : synthèse des conditions sociales, économiques et culturelles des "
           "familles des élèves, établie à partir des professions des parents ; plus il est élevé, plus le "
           "public accueilli est favorisé.",
    "va": "Valeur ajoutée : écart entre le résultat observé et le résultat attendu compte tenu du profil des "
          "élèves (âge, origine sociale, niveau scolaire). Positive, l'établissement fait mieux qu'attendu.",
    "remoteness": "Indice d'éloignement : accessibilité des ressources (équipements culturels, sportifs, "
                  "formations...) depuis l'établissement, base 100 ; plus il est élevé, plus le collège ou le "
                  "lycée est éloigné.",
}


class SchoolsService:
    def _national(self, db, groups):
        rows = db.query(SchoolNationalByYear).filter(SchoolNationalByYear.school_type.in_(list(groups))).all()
        out = {}
        for r in rows:
            out.setdefault(r.school_type, {}).setdefault(r.metric, {})[r.year] = {
                "establishments": r.establishments, "mean": num(r.mean),
                **{d: num(getattr(r, d)) for d in DECILES}}
        return out

    def _establishments(self, rows):
        schools = {}
        for r in rows:
            s = schools.setdefault(r.uai, {"uai": r.uai, "years": {}})
            for c in IDENTITY:
                if getattr(r, c) is not None:
                    s[c] = getattr(r, c)  # lignes triées par année : l'identité la plus récente l'emporte
            values = {}
            for col in SchoolByYear.__table__.columns.keys():
                if col in IDENTITY or col in ("uai", "year"):
                    continue
                v = getattr(r, col)
                if v is not None:
                    values[col] = int(v) if col.endswith("_decile") else num(v)
            s["years"][r.year] = values
        for s in schools.values():
            s["group"] = f"lycee_{s['lycee_type']}" if s.get("school_type") == "lycee" and s.get("lycee_type") \
                else s.get("school_type")
            s["latest"] = self._latest(s["years"])
        return sorted(schools.values(),
                      key=lambda s: (TYPE_ORDER.get(s.get("school_type"), 9), s.get("sector") != "public",
                                     s.get("name") or ""))

    @staticmethod
    def _latest(years):
        """Dernière année disponible de chaque famille d'indicateurs."""
        latest = {}
        for family, key in (("ips", "ips"), ("remoteness", "remoteness"), ("dnb", "dnb_success_rate"),
                            ("gt", "gt_success_rate"), ("pro", "pro_success_rate")):
            ys = [y for y, v in years.items() if v.get(key) is not None]
            if ys:
                latest[family] = max(ys)
        return latest

    def _get(self, commune_codes, territory):
        db = SessionLocal()
        try:
            rows = (db.query(SchoolByYear).filter(SchoolByYear.commune_code.in_(commune_codes))
                    .order_by(SchoolByYear.uai, SchoolByYear.year).all())
            establishments = self._establishments(rows)
            groups = {s["group"] for s in establishments} | {"ecole", "college", "lycee"}
            return {
                "territory": territory,
                "source": SOURCE,
                "definitions": DEFINITIONS,
                "establishments": establishments,
                "counts": {t: sum(1 for s in establishments if s.get("school_type") == t) for t in TYPE_ORDER},
                "national": self._national(db, groups),
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def by_commune(self, code):
        code = str(code).zfill(5)
        return self._get([code], {"level": "COM", "code": code})

    def by_epci(self, epci):
        db = SessionLocal()
        try:
            communes = [c[0] for c in db.query(GeoCode.codgeo).filter(GeoCode.epci == str(epci)).all()]
        finally:
            db.close()
        if not communes:
            return {"error": f"EPCI {epci} inconnu"}
        return self._get(communes, {"level": "EPCI", "code": str(epci), "communes": len(communes)})


class SixthGradeService(TerritoryStatsService):
    MODEL = SixthGradeAgeByTerritory
    DATA_KEY = "sixth_grade_data"
    LABEL = "âge à l'entrée en 6e"
    EXTRA = {"source": SOURCE + " — élèves entrant en 6e (public et privé sous contrat)"}
    EVOLUTION_METRICS = ["late_rate", "late_rate_girls", "late_rate_boys", "late_rate_public", "late_rate_private",
                         "early_rate"]

    def year_data(self, row):
        d = {}
        for g in ("total", "girls", "boys", "public", "private"):
            for m in ("pupils", "on_time", "early", "late"):
                d[f"{m}_{g}"] = num(getattr(row, f"{m}_{g}"))
        d["late_rate"] = pct(d["late_total"], d["pupils_total"])
        d["early_rate"] = pct(d["early_total"], d["pupils_total"])
        d["on_time_rate"] = pct(d["on_time_total"], d["pupils_total"])
        for g in ("girls", "boys", "public", "private"):
            d[f"late_rate_{g}"] = pct(d[f"late_{g}"], d[f"pupils_{g}"])
        return d
