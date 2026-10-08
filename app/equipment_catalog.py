"""
Catalogue des services clés de la Base permanente des équipements (BPE, INSEE) pour l'analyse des besoins sociaux.

Chaque service regroupe un ou plusieurs types d'équipements (TYPEQU). Utilisé par l'import
(scripts/import_equipment_by_territory.py : distances au service le plus proche) et par l'API
(app/services/equipment_service.py : densités pour 10 000 habitants, présence dans la commune).
  - density : la densité pour 10 000 habitants est comparée entre territoires
  - distance : la distance au plus proche est calculée pour les communes qui n'en ont pas
"""

SERVICES = {
    # Santé
    "general_practitioner": {"label": "Médecin généraliste", "theme": "Santé", "types": ["D265"],
                             "density": True, "distance": True},
    "nurse": {"label": "Infirmier", "theme": "Santé", "types": ["D281"], "density": True, "distance": True},
    "dentist": {"label": "Chirurgien-dentiste", "theme": "Santé", "types": ["D277"], "density": True,
                "distance": True},
    "physiotherapist": {"label": "Masseur-kinésithérapeute", "theme": "Santé", "types": ["D279"],
                        "density": True, "distance": True},
    "pharmacy": {"label": "Pharmacie", "theme": "Santé", "types": ["D307"], "density": True, "distance": True},
    "health_centre": {"label": "Maison ou centre de santé", "theme": "Santé", "types": ["D108", "D113"],
                      "density": False, "distance": True},
    "emergency": {"label": "Urgences", "theme": "Santé", "types": ["D106"], "density": False, "distance": True},
    "maternity": {"label": "Maternité", "theme": "Santé", "types": ["D107"], "density": False, "distance": True},
    "pmi": {"label": "Protection maternelle et infantile (PMI)", "theme": "Santé", "types": ["D115"],
            "density": False, "distance": True},
    # Petite enfance, enfance, familles
    "childcare": {"label": "Crèche ou micro-crèche", "theme": "Enfance et familles", "types": ["D502", "D509"],
                  "density": True, "distance": True},
    "childminder_hub": {"label": "Relais petite enfance", "theme": "Enfance et familles", "types": ["D504"],
                        "density": False, "distance": True},
    "leisure_centre": {"label": "Accueil de loisirs sans hébergement", "theme": "Enfance et familles",
                       "types": ["D505"], "density": False, "distance": True},
    "social_centre": {"label": "Centre social ou espace de vie sociale", "theme": "Enfance et familles",
                      "types": ["D506", "D508"], "density": False, "distance": True},
    "primary_school": {"label": "École maternelle, élémentaire ou primaire", "theme": "Enfance et familles",
                       "types": ["C107", "C108", "C109"], "density": False, "distance": True},
    "college": {"label": "Collège", "theme": "Enfance et familles", "types": ["C201"], "density": False,
                "distance": True},
    "lycee": {"label": "Lycée", "theme": "Enfance et familles", "types": ["C301", "C302", "C303"],
              "density": False, "distance": True},
    # Personnes âgées et handicap
    "elderly_housing": {"label": "Hébergement pour personnes âgées (Ehpad...)", "theme": "Personnes âgées et handicap",
                        "types": ["D401"], "density": True, "distance": True},
    "elderly_home_care": {"label": "Soins ou aide à domicile pour personnes âgées",
                          "theme": "Personnes âgées et handicap", "types": ["D402", "D403"], "density": False,
                          "distance": True},
    "disability": {"label": "Accueil ou service pour personnes handicapées", "theme": "Personnes âgées et handicap",
                   "types": ["D601", "D602", "D603", "D604", "D605", "D606", "D607"], "density": False,
                   "distance": True},
    # Services publics et accès aux droits
    "france_services": {"label": "France Services", "theme": "Services publics et accès aux droits",
                        "types": ["A128"], "density": False, "distance": True},
    "france_travail": {"label": "France Travail", "theme": "Services publics et accès aux droits",
                       "types": ["A122"], "density": False, "distance": True},
    "post": {"label": "Bureau, agence ou relais de poste", "theme": "Services publics et accès aux droits",
             "types": ["A206", "A207", "A208"], "density": False, "distance": True},
    "bank": {"label": "Banque", "theme": "Services publics et accès aux droits", "types": ["A203"],
             "density": False, "distance": True},
    "justice_access": {"label": "Maison de justice et du droit, point d'accès au droit",
                       "theme": "Services publics et accès aux droits", "types": ["A124", "A125", "A126"],
                       "density": False, "distance": True},
    "emergency_housing": {"label": "Hébergement d'urgence et d'insertion (CHRS...)",
                            "theme": "Services publics et accès aux droits",
                            "types": ["D703", "D704", "D710", "D711"], "density": False, "distance": False},
    # Commerces et vie quotidienne
    "supermarket": {"label": "Supermarché ou hypermarché", "theme": "Commerces et vie quotidienne",
                    "types": ["B104", "B105"], "density": False, "distance": True},
    "food_shop": {"label": "Commerce alimentaire de proximité", "theme": "Commerces et vie quotidienne",
                  "types": ["B201", "B202", "B204", "B206", "B207", "B208"], "density": True, "distance": True},
    "bakery": {"label": "Boulangerie", "theme": "Commerces et vie quotidienne", "types": ["B207"],
               "density": False, "distance": True},
    "train_station": {"label": "Gare", "theme": "Commerces et vie quotidienne", "types": ["E107", "E108", "E109"],
                      "density": False, "distance": True},
    # Sports, culture
    "library": {"label": "Bibliothèque", "theme": "Sports, culture et loisirs", "types": ["F307"],
                "density": False, "distance": True},
    "swimming_pool": {"label": "Bassin de natation", "theme": "Sports, culture et loisirs", "types": ["F101"],
                      "density": False, "distance": True},
    "cinema": {"label": "Cinéma", "theme": "Sports, culture et loisirs", "types": ["F303"], "density": False,
               "distance": True},
    "sports_hall": {"label": "Gymnase ou salle multisports", "theme": "Sports, culture et loisirs",
                    "types": ["F121"], "density": False, "distance": True},
}

DOMAINS = {
    "A": "Services pour les particuliers",
    "B": "Commerces",
    "C": "Enseignement",
    "D": "Santé et action sociale",
    "E": "Transports et déplacements",
    "F": "Sports, loisirs et culture",
    "G": "Tourisme",
}
