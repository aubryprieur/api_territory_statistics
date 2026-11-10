"""
Équipements géolocalisés (BPE 2025, INSEE — table equipment_points, scripts/import_equipment_points.py) et services
publics locaux de l'Annuaire de l'administration (DILA — mêmes table, types « DILA:<code pivot> »,
scripts/import_annuaire_points.py) : points d'une emprise (bbox WGS84) pour un groupe de types, pour les cartes de
localisation du tableau de bord.
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
    "shops": {
        "label": "Commerces et services de proximité",
        "categories": {
            "supermarket": ("Supermarché ou hypermarché", ["B104", "B105"]),
            "grocery": ("Supérette ou épicerie", ["B201", "B202"]),
            "bakery": ("Boulangerie-pâtisserie", ["B207"]),
            "food_other": ("Autre commerce alimentaire (boucherie, primeur, poissonnerie…)",
                           ["B204", "B205", "B206", "B208", "B209", "B210"]),
            "restaurant": ("Restaurant, restauration rapide", ["A504"]),
            "press": ("Librairie, papeterie, presse", ["B324", "B325"]),
            "pharmacy": ("Pharmacie", ["D307"]),
            "gp": ("Médecin généraliste", ["D265"]),
            "post": ("Bureau, relais ou agence postale", ["A206", "A207", "A208"]),
            "bank": ("Banque", ["A203"]),
            "hair_beauty": ("Coiffure, institut de beauté", ["A501", "A507"]),
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
    "public_services": {
        "label": "Services publics, accès aux droits et accompagnement social",
        "year": 2026,
        "source": ("DILA, Annuaire de l'administration — Base de données locales de Service-Public.fr (novembre 2026) ; "
                   "INSEE, Base permanente des équipements 2025 (hébergement, protection de l'enfance, médiation familiale)"),
        "categories": {
            "france_services": ("France services, point d'accueil numérique", ["DILA:france_services", "DILA:point_accueil_numerique"]),
            "town_hall": ("Mairie", ["DILA:mairie"]),
            "social_action": ("CCAS, action sociale du département (maison des solidarités, PMI…)",
                              ["DILA:ccas", "DILA:mds", "DILA:md", "DILA:mda", "DILA:pmi"]),
            "employment": ("France Travail, mission locale, Cap emploi, maison de l'emploi",
                           ["DILA:france_travail", "DILA:mission_locale", "DILA:cap_emploi", "DILA:maison_emploi"]),
            "social_security": ("CAF, CPAM, Carsat, MSA, Urssaf, Cicas",
                                ["DILA:caf", "DILA:cpam", "DILA:carsat", "DILA:msa", "DILA:urssaf", "DILA:cicas"]),
            "disability_ageing": ("MDPH, CLIC, aide aux aidants de personnes âgées",
                                  ["DILA:maison_handicapees", "DILA:clic", "DILA:accompagnement_personnes_agees"]),
            "youth": ("Information jeunesse, orientation (Info Jeunes, CIO)", ["DILA:cij", "DILA:cio"]),
            "rights_justice": ("Point-justice, maison de justice et du droit, CIDFF, Adil",
                               ["DILA:point_justice", "DILA:mjd", "DILA:cidf", "DILA:adil", "DILA:cdad"]),
            "taxes": ("Centre des finances publiques (impôts des particuliers)", ["DILA:sip"]),
            "security": ("Police, gendarmerie", ["DILA:commissariat_police", "DILA:gendarmerie", "DILA:police_municipale"]),
            # BPE ; ni D701 (hébergement de l'aide sociale à l'enfance) ni D711 (aide aux femmes en situation de
            # vulnérabilité), lieux qu'il vaut mieux ne pas pointer sur une carte publique
            "housing_inclusion": ("Hébergement et insertion (CHRS, demandeurs d'asile, pension de famille…)",
                                  ["D703", "D704", "D705", "D710"]),
            "child_family": ("Point info famille, médiation familiale, action éducative (protection de l'enfance)",
                             ["DILA:pif", "D507", "D702"]),
        },
    },
}
DILA_TYPES = sorted({t for g in GROUPS.values() for _, types in g["categories"].values() for t in types if t.startswith("DILA:")})
BPE_TYPES = sorted({t for g in GROUPS.values() for _, types in g["categories"].values() for t in types if not t.startswith("DILA:")})
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
            return {"group": group, "label": g["label"], "year": g.get("year", YEAR), "source": g.get("source", SOURCE),
                    "categories": {k: lbl for k, (lbl, _) in g["categories"].items()},
                    "bbox": [west, south, east, north], "truncated": len(rows) > MAX_POINTS, "points": points}
        except SQLAlchemyError as e:
            return {"error": str(e)}
        finally:
            db.close()
