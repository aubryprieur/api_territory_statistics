"""
Familles — données INSEE du recensement (DS_RP_FAMILLE_COMP), table families_by_territory.

Les effectifs sont les valeurs officielles INSEE à chaque échelle (commune, EPCI,
département, région, France métropolitaine) : aucune agrégation n'est faite ici.
Seuls les taux sont calculés, à partir des effectifs de la même ligne.

Millésimes disponibles : 2012, 2017, 2023.
Par défaut, l'évolution compare le dernier millésime au millésime situé 5 à 6 ans
plus tôt (2017 -> 2023).
"""
import math

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import FamilyByTerritory, GeoCode

FRANCE_CODE = "FM"  # France métropolitaine
MIN_EVOLUTION_GAP = 5  # années minimum entre millésime de comparaison et dernier millésime

PARENT_TYPES = ["father_employed", "father_not_employed", "mother_employed", "mother_not_employed",
                "couple_both_employed", "couple_man_only_employed", "couple_woman_only_employed",
                "couple_none_employed"]
CHILD_AGES = ["lt2", "2_5"]  # moins de 2 ans, 2 à 5 ans (tableau détaillé 2023)

COUNT_FIELDS = [
    "total_families",
    "couples_with_children",
    "couples_without_children",
    "single_parent_families",
    "single_fathers",
    "single_mothers",
    "blended_families",
    "traditional_families",
    "families_0_children",
    "families_1_child",
    "families_2_children",
    "families_3_children",
    "families_4_plus_children",
] + [f"children_{a}_{t}" for a in CHILD_AGES for t in PARENT_TYPES]

EVOLUTION_METRICS = [
    "total_families",
    "couples_with_children", "couples_with_children_percentage",
    "couples_without_children", "couples_without_children_percentage",
    "single_parent_families", "single_parent_families_percentage",
    "single_fathers", "single_mothers",
    "families_with_3_children", "families_with_4_plus_children",
    "total_large_families", "large_families_percentage",
    "blended_families", "blended_families_percentage",
]


def _num(value):
    """float ou None (valeur absente / NaN)."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def _pct(part, total):
    if part is None or not total:
        return None
    return round(part / total * 100, 2)


def _zero(value):
    return value if value is not None else 0.0


class FamilyService:

    # ------------------------------------------------------------------ format
    def _year_data(self, row):
        """Effectifs + taux pour une ligne (un territoire, un millésime)."""
        c = {f: _num(getattr(row, f)) for f in COUNT_FIELDS}
        total = c["total_families"]
        f3, f4 = c["families_3_children"], c["families_4_plus_children"]
        large = (f3 + f4) if f3 is not None and f4 is not None else None

        return {
            # Noms historiques conservés pour le dashboard
            "total_families": c["total_families"],
            "couples_with_children": c["couples_with_children"],
            "couples_without_children": c["couples_without_children"],
            "single_parent_families": c["single_parent_families"],
            "single_fathers": c["single_fathers"],
            "single_mothers": c["single_mothers"],
            "families_with_3_children": f3,
            "families_with_4_plus_children": f4,
            "total_large_families": large,
            # Nouveaux effectifs
            "blended_families": c["blended_families"],
            "traditional_families": c["traditional_families"],
            "families_0_children": c["families_0_children"],
            "families_1_child": c["families_1_child"],
            "families_2_children": c["families_2_children"],
            # Taux (en % de l'ensemble des familles, sauf mention)
            "couples_with_children_percentage": _pct(c["couples_with_children"], total),
            "couples_without_children_percentage": _pct(c["couples_without_children"], total),
            "single_parent_families_percentage": _pct(c["single_parent_families"], total),
            "large_families_percentage": _pct(large, total),
            "families_3_children_percentage": _pct(f3, total),
            "families_4_plus_children_percentage": _pct(f4, total),
            # % des familles monoparentales
            "single_fathers_percentage": _pct(c["single_fathers"], c["single_parent_families"]),
            "single_mothers_percentage": _pct(c["single_mothers"], c["single_parent_families"]),
            # % des couples avec enfant(s)
            "blended_families_percentage": _pct(c["blended_families"], c["couples_with_children"]),
            "traditional_families_percentage": _pct(c["traditional_families"], c["couples_with_children"]),
            # Enfants de moins de 2 ans et de 2-5 ans selon l'activité des parents (2023)
            **self._children_by_parents_activity(c),
        }

    def _children_by_parents_activity(self, c):
        """Répartition des jeunes enfants selon la situation d'emploi de leurs parents (en % des enfants)."""
        out = {}
        for a in CHILD_AGES:
            v = {t: c[f"children_{a}_{t}"] for t in PARENT_TYPES}
            if all(x is None for x in v.values()):
                continue
            total = sum(x for x in v.values() if x is not None)
            out[f"children_{a}_total"] = total
            for t, x in v.items():
                out[f"children_{a}_{t}"] = x
                out[f"children_{a}_{t}_percentage"] = _pct(x, total)
            groups = {
                # tous les parents présents ont un emploi (besoin potentiel de mode de garde)
                "all_parents_employed": ["father_employed", "mother_employed", "couple_both_employed"],
                # aucun parent en emploi (fragilité économique)
                "no_parent_employed": ["father_not_employed", "mother_not_employed", "couple_none_employed"],
                "single_parent": ["father_employed", "father_not_employed", "mother_employed", "mother_not_employed"],
                "couple_one_employed": ["couple_man_only_employed", "couple_woman_only_employed"],
            }
            for g, types in groups.items():
                out[f"children_{a}_{g}_percentage"] = _pct(sum(v[t] or 0 for t in types), total)
        return out

    def _default_period(self, years):
        """Dernier millésime et millésime situé au moins 5 ans plus tôt (le plus récent)."""
        end = years[-1]
        earlier = [y for y in years if y <= end - MIN_EVOLUTION_GAP]
        start = earlier[-1] if earlier else years[0]
        return start, end

    def _calculate_evolution(self, data, start_year, end_year):
        years = sorted(data.keys())
        if len(years) < 2:
            return {}
        default_start, default_end = self._default_period(years)
        start_year = start_year or default_start
        end_year = end_year or default_end
        if start_year not in data or end_year not in data:
            return {"error": f"Millésimes disponibles : {', '.join(map(str, years))}"}

        evolutions = {}
        for metric in EVOLUTION_METRICS:
            v0, v1 = data[start_year].get(metric), data[end_year].get(metric)
            if v0 is None or v1 is None:
                continue  # ex. familles recomposées : 2023 uniquement
            evolutions[metric] = {
                "start_value": v0,
                "end_value": v1,
                "evolution_percentage": round((v1 - v0) / v0 * 100, 2) if v0 else 0.0,
                "period": f"{start_year}-{end_year}",
            }
        return evolutions

    def _get(self, level, code, start_year=None, end_year=None):
        db = SessionLocal()
        try:
            rows = (
                db.query(FamilyByTerritory)
                .filter(FamilyByTerritory.geo_level == level, FamilyByTerritory.geo_code == str(code))
                .order_by(FamilyByTerritory.year)
                .all()
            )
            if not rows:
                return {"error": f"Aucune donnée familles pour {level} {code}"}

            data = {row.year: self._year_data(row) for row in rows}
            years = sorted(data)
            start, end = self._default_period(years)
            return {
                "territory": {"level": level, "code": str(code)},
                "available_years": years,
                "latest_year": end,
                "comparison_year": start,
                "family_data": data,
                "evolution": self._calculate_evolution(data, start_year, end_year),
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    # ------------------------------------------------------------ territoires
    def get_families_by_commune(self, geo_code: str, start_year: int = None, end_year: int = None):
        code = str(geo_code).zfill(5)
        result = self._get("COM", code, start_year, end_year)
        if "error" in result:
            # Arrondissements municipaux de Paris, Lyon, Marseille
            arm = self._get("ARM", code, start_year, end_year)
            if "error" not in arm:
                return arm
        return result

    def get_families_by_epci(self, epci: str, start_year: int = None, end_year: int = None):
        return self._get("EPCI", epci, start_year, end_year)

    def get_families_by_department(self, dep: str, start_year: int = None, end_year: int = None):
        dep = str(dep)
        if dep.isdigit() and len(dep) < 2:
            dep = dep.zfill(2)
        return self._get("DEP", dep, start_year, end_year)

    def get_families_by_region(self, reg: str, start_year: int = None, end_year: int = None):
        return self._get("REG", str(reg).zfill(2), start_year, end_year)

    def get_families_france(self, start_year: int = None, end_year: int = None):
        """France métropolitaine."""
        return self._get("FRANCE", FRANCE_CODE, start_year, end_year)

    # ------------------------------------------- EPCI : détail par commune
    def _epci_communes(self, db, epci):
        communes = db.query(GeoCode.codgeo, GeoCode.libgeo).filter(GeoCode.epci == str(epci)).all()
        epci_info = db.query(GeoCode.libepci).filter(GeoCode.epci == str(epci)).first()
        epci_name = epci_info[0] if epci_info and epci_info[0] else f"EPCI {epci}"
        latest_year = None
        rows = {}
        if communes:
            codes = [c for c, _ in communes]
            q = db.query(FamilyByTerritory).filter(
                FamilyByTerritory.geo_level == "COM", FamilyByTerritory.geo_code.in_(codes)
            )
            all_rows = q.all()
            if all_rows:
                latest_year = max(r.year for r in all_rows)
                rows = {r.geo_code: r for r in all_rows if r.year == latest_year}
        return communes, epci_name, latest_year, rows

    def get_couples_with_children_by_epci(self, epci: str):
        db = SessionLocal()
        try:
            communes, epci_name, year, rows = self._epci_communes(db, epci)
            communes_data, tot, tot_cwc = [], 0.0, 0.0
            for code, name in communes:
                r = rows.get(code)
                total = _zero(_num(r.total_families)) if r else 0.0
                cwc = _zero(_num(r.couples_with_children)) if r else 0.0
                communes_data.append({
                    "code": code, "name": name,
                    "total_households": total,  # = nombre de familles (nom historique)
                    "couples_with_children": cwc,
                    "couples_with_children_percentage": _pct(cwc, total) or 0.0,
                })
                tot += total
                tot_cwc += cwc
            communes_data.sort(key=lambda x: x["couples_with_children_percentage"], reverse=True)
            return {
                "epci": epci, "epci_name": epci_name, "year": year,
                "communes_count": len(communes),
                "total_households": tot,
                "total_couples_with_children": tot_cwc,
                "epci_couples_with_children_percentage": _pct(tot_cwc, tot) or 0.0,
                "communes": communes_data,
            }
        finally:
            db.close()

    def get_single_parent_families_by_epci(self, epci: str):
        db = SessionLocal()
        try:
            communes, epci_name, year, rows = self._epci_communes(db, epci)
            communes_data = []
            tot = tot_sp = tot_f = tot_m = 0.0
            for code, name in communes:
                r = rows.get(code)
                total = _zero(_num(r.total_families)) if r else 0.0
                sp = _zero(_num(r.single_parent_families)) if r else 0.0
                f = _zero(_num(r.single_fathers)) if r else 0.0
                m = _zero(_num(r.single_mothers)) if r else 0.0
                communes_data.append({
                    "code": code, "name": name,
                    "total_households": total,
                    "single_parent_families": sp,
                    "single_fathers": f,
                    "single_mothers": m,
                    "single_parent_percentage": _pct(sp, total) or 0.0,
                    "single_father_percentage": _pct(f, sp) or 0.0,
                    "single_mother_percentage": _pct(m, sp) or 0.0,
                })
                tot += total; tot_sp += sp; tot_f += f; tot_m += m
            communes_data.sort(key=lambda x: x["single_parent_percentage"], reverse=True)
            return {
                "epci": epci, "epci_name": epci_name, "year": year,
                "communes_count": len(communes),
                "total_households": tot,
                "total_single_parent_families": tot_sp,
                "total_single_fathers": tot_f,
                "total_single_mothers": tot_m,
                "epci_single_parent_percentage": _pct(tot_sp, tot) or 0.0,
                "epci_single_father_percentage": _pct(tot_f, tot_sp) or 0.0,
                "epci_single_mother_percentage": _pct(tot_m, tot_sp) or 0.0,
                "communes": communes_data,
            }
        finally:
            db.close()

    def get_large_families_by_epci(self, epci: str):
        db = SessionLocal()
        try:
            communes, epci_name, year, rows = self._epci_communes(db, epci)
            communes_data = []
            tot = tot_large = tot_3 = tot_4 = 0.0
            for code, name in communes:
                r = rows.get(code)
                total = _zero(_num(r.total_families)) if r else 0.0
                f3 = _zero(_num(r.families_3_children)) if r else 0.0
                f4 = _zero(_num(r.families_4_plus_children)) if r else 0.0
                communes_data.append({
                    "code": code, "name": name,
                    "total_households": total,
                    "large_families": f3 + f4,
                    "families_3_children": f3,
                    "families_4_plus_children": f4,
                    "large_families_percentage": _pct(f3 + f4, total) or 0.0,
                    "families_3_children_percentage": _pct(f3, total) or 0.0,
                    "families_4_plus_percentage": _pct(f4, total) or 0.0,
                })
                tot += total; tot_large += f3 + f4; tot_3 += f3; tot_4 += f4
            communes_data.sort(key=lambda x: x["large_families_percentage"], reverse=True)
            return {
                "epci": epci, "epci_name": epci_name, "year": year,
                "communes_count": len(communes),
                "total_households": tot,
                "total_large_families": tot_large,
                "total_families_3_children": tot_3,
                "total_families_4_plus_children": tot_4,
                "epci_large_families_percentage": _pct(tot_large, tot) or 0.0,
                "epci_families_3_children_percentage": _pct(tot_3, tot) or 0.0,
                "epci_families_4_plus_percentage": _pct(tot_4, tot) or 0.0,
                "communes": communes_data,
            }
        finally:
            db.close()
