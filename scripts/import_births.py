import sys
import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement avant d'importer les modules qui en dépendent
load_dotenv()

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import Birth

def clean_births_table():
    """Nettoie la table births en supprimant toutes les données existantes."""
    logger.info("🗑️ Nettoyage de la table births...")
    try:
        with engine.connect() as connection:
            # Utilisation de TRUNCATE pour un nettoyage rapide et efficace
            connection.execute(text("TRUNCATE TABLE births RESTART IDENTITY CASCADE"))
        logger.info("✅ Table births nettoyée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table births : {e}")
        raise

def import_csv_to_db():
    try:
        # Nettoyer la table avant l'importation
        clean_births_table()

        logger.info("📥 Chargement des données depuis le fichier CSV...")

        # Charger le fichier CSV
        file_path = "data/births/DS_ETAT_CIVIL_NAIS_COMMUNES_data.csv"
        df = pd.read_csv(file_path, delimiter=";", encoding="utf-8", low_memory=False)

        # Renommer les colonnes pour correspondre aux noms des colonnes de la base
        df = df.rename(columns={
            "GEO": "geo",
            "GEO_OBJECT": "geo_object",
            "TIME_PERIOD": "time_period",
            "OBS_VALUE": "obs_value"
        })

        # Sélectionner uniquement les colonnes nécessaires
        df = df[["geo", "geo_object", "time_period", "obs_value"]]

        # Vérifier les 5 premières lignes
        logger.info("Aperçu des données à importer :")
        logger.info(df.head().to_string())

        # Connexion à la base de données
        session = SessionLocal()

        try:
            logger.info("🗄️ Insertion des données dans la base PostgreSQL...")
            session.bulk_insert_mappings(Birth, df.to_dict(orient="records"))
            session.commit()
            logger.info(f"✅ {len(df)} enregistrements importés avec succès dans la table `births` !")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erreur lors de l'importation des données : {e}")
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ Erreur globale lors de l'importation : {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de naissances")
    import_csv_to_db()
    logger.info("🏁 Import terminé")
