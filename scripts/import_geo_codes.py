import sys
import os
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app
from app.database import SessionLocal
from app.models import GeoCode

# Chemin du fichier CSV
CSV_FILE = "data/geography/COG_au_01-01-2024.csv"

def clean_str(value):
    """ Nettoie et retourne une chaîne de caractères ou None si invalide. """
    return str(value).strip() if pd.notna(value) else None

def clean_geo_codes_table():
    """Nettoie la table geo_codes en supprimant toutes les données."""
    db: Session = SessionLocal()
    try:
        logger.info("🗑️ Nettoyage de la table geo_codes...")
        # Supprimer toutes les données de la table
        deleted_count = db.query(GeoCode).delete()
        db.commit()
        logger.info(f"✅ {deleted_count} enregistrements supprimés de la table geo_codes")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        db.rollback()
    finally:
        db.close()

def import_geo_codes():
    # Nettoyer la table avant l'import
    clean_geo_codes_table()

    db: Session = SessionLocal()
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"❌ Fichier introuvable : {CSV_FILE}")
            return

        logger.info(f"📥 Importing {CSV_FILE}...")

        # Charger le CSV en DataFrame
        df = pd.read_csv(CSV_FILE, sep=";", dtype=str, engine="python")
        df.columns = df.columns.str.strip()  # Supprimer les espaces invisibles
        logger.info(f"📌 Colonnes après correction : {df.columns.tolist()}")  # Vérifier les colonnes

        # Vérification des colonnes attendues
        expected_cols = ["CODGEO", "LIBGEO", "EPCI", "LIBEPCI", "DEP", "REG"]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"⚠️ Colonnes absentes dans le fichier : {missing_cols}")
            return

        # Renommage des colonnes pour correspondre au modèle
        df = df.rename(columns={
            "CODGEO": "codgeo",
            "LIBGEO": "libgeo",
            "EPCI": "epci",
            "LIBEPCI": "libepci",
            "DEP": "dep",
            "REG": "reg"
        })

        # Nettoyage des données pour `VARCHAR`
        df["codgeo"] = df["codgeo"].apply(clean_str)
        df["libgeo"] = df["libgeo"].apply(clean_str)
        df["epci"] = df["epci"].apply(clean_str)
        df["libepci"] = df["libepci"].apply(clean_str)
        df["dep"] = df["dep"].apply(clean_str)
        df["reg"] = df["reg"].apply(clean_str)

        # Vérification des valeurs suspectes avant insertion
        logger.info(f"🔍 Valeurs uniques dans EPCI : {df['epci'].unique()[:10]}")

        # Insérer en base de données avec `bulk_save_objects` pour plus d'efficacité
        geo_entries = [
            GeoCode(**row.dropna().to_dict())  # Exclut les NaN
            for _, row in df.iterrows()
        ]

        db.bulk_save_objects(geo_entries)
        db.commit()
        logger.info(f"✅ Imported {len(geo_entries)} rows.")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"❌ Erreur d'intégrité lors de l'import : {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur générale lors de l'import : {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des codes géographiques")
    import_geo_codes()
    logger.info("🏁 Import terminé")
