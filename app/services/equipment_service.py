"""
Équipements et services — INSEE, Base permanente des équipements (BPE 2025), tables equipment_types,
equipment_by_territory et equipment_nearest (scripts/import_equipment_by_territory.py).

Pour une commune :
  - services clés (app/equipment_catalog.SERVICES) : nombre dans la commune, dont en quartier prioritaire, densité
    pour 10 000 habitants (recensement 2023) comparée à l'EPCI, au département, à la région et à la France
    métropolitaine, et pour les services absents, distance à vol d'oiseau au plus proche
  - inventaire complet des équipements de la commune par domaine et sous-domaine
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.equipment_catalog import DOMAINS, SERVICES
from app.models import EquipmentByTerritory, EquipmentNearest, EquipmentType, GeoCode, PopulationByTerritory

YEAR = 2025
POPULATION_YEAR = 2023
SOURCE = "INSEE, Base permanente des équipements 2025 ; population : recensement 2023"
LEVELS = {"commune": "COM", "epci": "EPCI", "department": "DEP", "region": "REG", "france": "FRANCE"}


def _density(count, population):
    return round(count / population * 10000, 1) if count is not None and population else None


class EquipmentService:
    def _counts(self, db, level, code):
        rows = (db.query(EquipmentByTerritory)
                .filter(EquipmentByTerritory.geo_level == level, EquipmentByTerritory.geo_code == code,
                        EquipmentByTerritory.year == YEAR).all())
        return {r.typequ: (r.count or 0, r.count_qpv or 0) for r in rows}

    def _population(self, db, level, code):
        row = (db.query(PopulationByTerritory.pop)
               .filter(PopulationByTerritory.geo_level == level, PopulationByTerritory.geo_code == code,
                       PopulationByTerritory.year == POPULATION_YEAR).first())
        return float(row[0]) if row and row[0] is not None else None

    def _parents(self, db, code):
        geo = db.query(GeoCode).filter(GeoCode.codgeo == code).first()
        parents = {}
        if geo is not None:
            parents = {"epci": geo.epci, "department": geo.dep, "region": geo.reg}
        else:
            parents = {"department": code[:3] if code.startswith("97") else code[:2]}
        parents["france"] = "FM"
        return {k: str(v) for k, v in parents.items() if v}

    def _get(self, level, code):
        db = SessionLocal()
        try:
            counts = self._counts(db, level, code)
            if not counts:
                return {"error": f"Aucun équipement recensé pour {level} {code}"}
            population = self._population(db, level, code)
            comparison = {}
            if level in ("COM", "ARM"):
                for key, pcode in self._parents(db, code).items():
                    plevel = LEVELS[key]
                    comparison[key] = {"code": pcode, "population": self._population(db, plevel, pcode),
                                       "counts": self._counts(db, plevel, pcode)}
            nearest = {}
            if level in ("COM", "ARM"):
                for r in (db.query(EquipmentNearest)
                          .filter(EquipmentNearest.geo_code == code, EquipmentNearest.year == YEAR).all()):
                    nearest[r.service] = {"distance_km": r.distance_km, "commune_code": r.nearest_code,
                                          "commune_name": r.nearest_name}
            services = []
            for key, svc in SERVICES.items():
                count = sum(counts.get(t, (0, 0))[0] for t in svc["types"])
                count_qpv = sum(counts.get(t, (0, 0))[1] for t in svc["types"])
                item = {"key": key, "label": svc["label"], "theme": svc["theme"], "types": svc["types"],
                        "count": count, "count_qpv": count_qpv, "density_compared": svc["density"],
                        "density": _density(count, population), "nearest": nearest.get(key) if count == 0 else None}
                if svc["density"]:
                    item["comparison"] = {
                        k: _density(sum(c["counts"].get(t, (0, 0))[0] for t in svc["types"]), c["population"])
                        for k, c in comparison.items()}
                services.append(item)
            labels = {t.typequ: t for t in db.query(EquipmentType).filter(EquipmentType.typequ.in_(list(counts))).all()}
            inventory = {}
            for typequ, (count, count_qpv) in sorted(counts.items()):
                t = labels.get(typequ)
                dom = inventory.setdefault(typequ[0], {"domain": typequ[0],
                                                       "label": DOMAINS.get(typequ[0], typequ[0]),
                                                       "count": 0, "count_qpv": 0, "subdomains": {}})
                dom["count"] += count
                dom["count_qpv"] += count_qpv
                sub = dom["subdomains"].setdefault(typequ[:2], {"subdomain": typequ[:2],
                                                                "label": t.subdomain_label if t else typequ[:2],
                                                                "items": []})
                sub["items"].append({"typequ": typequ, "label": t.label if t else typequ, "count": count,
                                     "count_qpv": count_qpv})
            for dom in inventory.values():
                dom["subdomains"] = list(dom["subdomains"].values())
            return {
                "territory": {"level": level, "code": code},
                "year": YEAR, "population_year": POPULATION_YEAR, "source": SOURCE,
                "population": population,
                "totals": {"count": sum(c for c, _ in counts.values()), "count_qpv": sum(q for _, q in counts.values())},
                "comparison_territories": {k: {"code": c["code"], "population": c["population"]}
                                           for k, c in comparison.items()},
                "services": services,
                "inventory": [inventory[k] for k in sorted(inventory)],
            }
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()

    def by_commune(self, code):
        code = str(code).zfill(5)
        result = self._get("COM", code)
        if "error" in result:
            arm = self._get("ARM", code)
            if "error" not in arm:
                return arm
        return result

    def by_epci(self, code):
        return self._get("EPCI", str(code))
