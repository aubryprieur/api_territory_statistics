"""
Équipements géolocalisés (BPE 2025, INSEE — table equipment_points, scripts/import_equipment_points.py) : points d'une
emprise (bbox WGS84) pour un groupe de types, pour les cartes de localisation du tableau de bord.
"""
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import EquipmentPoint

YEAR = 2025
# Groupes de types (TYPEQU) : catégorie affichée -> types BPE
GROUPS = {
    "youth": {
        "label": "Équipements pour les enfants et les jeunes",
        "categories": {
            "leisure_centre": ("Accueil de loisirs sans hébergement", ["D505"]),
            "social_centre": ("Centre social ou espace de vie sociale", ["D506", "D508"]),
            "college": ("Collège", ["C201"]),
            "lycee": ("Lycée", ["C301", "C302", "C303"]),
            "library": ("Bibliothèque", ["F307"]),
            "sports_hall": ("Gymnase ou salle multisports", ["F121"]),
            "big_fields": ("Terrain de grands jeux", ["F113"]),
            "outdoor_fields": ("Plateau ou terrain de jeux extérieur", ["F111"]),
            "swimming_pool": ("Bassin de natation", ["F101"]),
            "cinema": ("Cinéma", ["F303"]),
        },
    },
    "local_life": {
        "label": "Équipements de la vie locale",
        "categories": {
            "social_centre": ("Centre social ou espace de vie sociale", ["D506", "D508"]),
            "library": ("Bibliothèque, médiathèque", ["F307"]),
            "cinema": ("Cinéma", ["F303"]),
            "conservatoire": ("Conservatoire", ["F305"]),
            "performing_arts": ("Salle de spectacle", ["F315"]),
            "exhibition": ("Lieu d'exposition et de médiation culturelle", ["F312"]),
            "sports_hall": ("Gymnase ou salle de sport", ["F121", "F114", "F116", "F129"]),
            "big_fields": ("Terrain de grands jeux", ["F113"]),
            "outdoor_fields": ("Plateau, terrain extérieur ou skatepark", ["F111", "F130"]),
            "swimming_pool": ("Bassin de natation", ["F101"]),
            "tennis": ("Court de tennis", ["F103"]),
            "other_sport": ("Autre équipement sportif (athlétisme, équitation, parcours…)",
                            ["F102", "F106", "F107", "F109", "F110", "F118", "F123", "F127", "F128"]),
        },
    },
    "early_childhood": {
        "label": "Équipements pour la petite enfance",
        "categories": {
            "eaje": ("Établissement d'accueil du jeune enfant (crèche)", ["D502"]),
            "micro_creche": ("Micro-crèche", ["D509"]),
            "rpe": ("Relais petite enfance", ["D504"]),
            "laep": ("Lieu d'accueil enfant-parent", ["D503"]),
            "pmi": ("Protection maternelle et infantile (PMI)", ["D115"]),
            "maternelle": ("École maternelle", ["C107"]),
            "primaire": ("École primaire ou élémentaire", ["C108", "C109"]),
        },
    },
    "seniors": {
        "label": "Équipements et services pour les personnes âgées",
        "categories": {
            "elderly_housing": ("Hébergement pour personnes âgées (Ehpad, résidence autonomie…)", ["D401"]),
            "home_nursing": ("Soins infirmiers à domicile", ["D402"]),
            "home_help": ("Aide à domicile", ["D403"]),
            "health_centre": ("Maison ou centre de santé", ["D108", "D113"]),
        },
    },
}
ALL_TYPES = sorted({t for g in GROUPS.values() for _, types in g["categories"].values() for t in types})
QUALITY = {"A": "acceptable", "B": "bonne", "M": "mauvaise", "_U": "indéterminée", "_Z": "sans objet"}
SOURCE = "INSEE, Base permanente des équipements 2025 (localisation des équipements)"
MAX_POINTS = 20000


class EquipmentPointsService:
    def by_bbox(self, west, south, east, north, group="youth"):
        g = GROUPS.get(group)
        if g is None:
            return {"error": f"Groupe inconnu : {group}"}
        type_to_cat = {t: k for k, (_, types) in g["categories"].items() for t in types}
        db = SessionLocal()
        try:
            rows = (db.query(EquipmentPoint)
                    .filter(EquipmentPoint.typequ.in_(list(type_to_cat)),
                            EquipmentPoint.lat >= south, EquipmentPoint.lat <= north,
                            EquipmentPoint.lon >= west, EquipmentPoint.lon <= east)
                    .limit(MAX_POINTS + 1).all())
            points = [{"category": type_to_cat[r.typequ], "typequ": r.typequ, "name": r.name, "depcom": r.depcom,
                       "commune": r.commune_name, "epci": r.epci, "lat": round(r.lat, 5), "lon": round(r.lon, 5),
                       "qpv": r.qpv, "quality": QUALITY.get(r.quality)} for r in rows[:MAX_POINTS]]
            return {"group": group, "label": g["label"], "year": YEAR, "source": SOURCE,
                    "categories": {k: lbl for k, (lbl, _) in g["categories"].items()},
                    "bbox": [west, south, east, north], "truncated": len(rows) > MAX_POINTS, "points": points}
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()
