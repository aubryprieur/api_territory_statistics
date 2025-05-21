import sys
import os
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy import exists

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app (load_dotenv est déjà appelé par app.database)
from app.database import SessionLocal
from app.models import Family

# Configuration des fichiers et des années
DATA_PATH = "data/families/commune"
YEARS = [2017, 2018, 2019, 2020, 2021]

# Mapping des colonnes correctes
COLUMN_MAPPING = {
    "CODGEO": "geo_code",
    "C{year}_FAM": "total_households",
    "C{year}_COUPAENF": "couples_with_children",
    "C{year}_FAMMONO": "single_parent_families",
    "C{year}_HMONO": "single_fathers",
    "C{year}_FMONO": "single_mothers",
    "C{year}_COUPSENF": "couples_without_children",
    "C{year}_NE24F3": "children_under_24_three_siblings",
    "C{year}_NE24F4P": "children_under_24_four_or_more_siblings",
}

def normalize_geo_code(code):
    """Normalise un code géographique au format standard INSEE (5 chiffres)"""
    if pd.isna(code) or code is None:
        return None
    return str(code).zfill(5)

def clean_families_table():
    """Nettoie la table families en supprimant toutes les données."""
    db: Session = SessionLocal()
    try:
        logger.info("🗑️ Nettoyage de la table families...")
        # Supprimer toutes les données de la table
        deleted_count = db.query(Family).delete()
        db.commit()
        logger.info(f"✅ {deleted_count} enregistrements supprimés de la table families")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        db.rollback()
    finally:
        db.close()

def import_family_data():
    """Importe les données des familles depuis les fichiers CSV."""
    db: Session = SessionLocal()
    try:
        # D'abord, nettoyer la table
        clean_families_table()

        total_records = 0
        for year in YEARS:
            file_path = os.path.join(DATA_PATH, f"base-cc-coupl-fam-men-{year}.CSV")
            if not os.path.exists(file_path):
                logger.error(f"❌ Fichier introuvable : {file_path}")
                continue

            logger.info(f"📥 Importing {file_path}...")

            # Charger le CSV en DataFrame
            df = pd.read_csv(file_path, sep=";", dtype=str)
            df.columns = df.columns.str.strip()  # Supprimer les espaces invisibles

            # Générer le dictionnaire de renommage avec les colonnes au bon format
            short_year = str(year)[2:]
            rename_dict = {col.format(year=short_year): name for col, name in COLUMN_MAPPING.items()}

            # Vérifier les colonnes manquantes
            missing_columns = [col for col in rename_dict.keys() if col not in df.columns]
            if missing_columns:
                logger.warning(f"⚠️ Colonnes absentes dans le fichier {year} : {missing_columns}")
                continue

            # Renommer les colonnes et ajouter l'année
            df = df.rename(columns=rename_dict)
            df["year"] = year

            # Sélectionner uniquement les colonnes utiles
            df = df[list(rename_dict.values()) + ["year"]].dropna(how="all")

            # ********* NORMALISATION DES CODES GÉOGRAPHIQUES **********
            # Standardiser tous les codes de communes à 5 chiffres
            df["geo_code"] = df["geo_code"].apply(normalize_geo_code)

            # Vérifier et signaler les codes potentiellement problématiques
            code_lengths = df["geo_code"].str.len().value_counts()
            logger.info(f"📊 Distribution des longueurs de codes géographiques après normalisation: {code_lengths.to_dict()}")

            if len(code_lengths) > 1 or (5 not in code_lengths):
                logger.warning("⚠️ Certains codes géographiques n'ont pas une longueur de 5 caractères après normalisation!")

                # Afficher quelques exemples
                problematic_codes = df[df["geo_code"].str.len() != 5]["geo_code"].unique()[:10]
                logger.warning(f"⚠️ Exemples de codes problématiques: {problematic_codes}")
            # ********************************************************

            # Convertir les valeurs numériques
            numeric_cols = [col for col in rename_dict.values() if col != "geo_code"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

            # Insérer les données en lot
            records = df.to_dict('records')

            # Insérer par lots pour améliorer les performances et limiter l'utilisation de mémoire
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                db.bulk_insert_mappings(Family, batch)
                db.commit()
                logger.info(f"  - Progression: {min(i+batch_size, len(records))}/{len(records)} enregistrements")

            total_records += len(df)
            logger.info(f"✅ Importé {len(df)} enregistrements pour {year}")

        logger.info(f"🏁 Import terminé avec succès! {total_records} enregistrements au total.")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation : {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de familles")
    import_family_data()
    logger.info("🏁 Import terminé")
