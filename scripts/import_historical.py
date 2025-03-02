import sys
import os
import pandas as pd
from pathlib import Path
import logging
import sqlalchemy as sa

# Ajouter le répertoire racine du projet au chemin d'importation
# Cette ligne doit être avant toute tentative d'importation des modules app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app (load_dotenv est déjà appelé par app.database)
from app.database import engine, Base, SessionLocal
from app.models import Historical

def clean_database():
    """Nettoie la table historical"""
    try:
        with engine.connect() as conn:
            metadata = sa.MetaData()
            # Vérifier si la table existe
            inspector = sa.inspect(engine)
            if 'historical' in inspector.get_table_names():
                logger.info("🗑️ Suppression de la table historical existante...")
                conn.execute(sa.text("DROP TABLE historical CASCADE"))
                logger.info("✅ Table supprimée avec succès")
            else:
                logger.info("ℹ️ Aucune table historical à supprimer")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la base : {str(e)}")
        raise

def create_historical_table():
    """Crée la table historical avec SQLAlchemy"""
    try:
        with engine.connect() as conn:
            logger.info("🔧 Création de la table historical...")

            # Création de la table en utilisant le modèle SQLAlchemy
            Historical.__table__.create(engine)
            logger.info("✅ Table historical créée")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la table : {str(e)}")
        raise

def import_historical_data():
    try:
        # Nettoyer la base d'abord
        clean_database()

        # Créer la table historical
        create_historical_table()

        # Vérifier le fichier
        file_path = Path("data/base-cc-serie-historique-2021.csv")
        if not file_path.exists():
            logger.error(f"❌ Fichier non trouvé : {file_path}")
            return
        logger.info(f"✅ Fichier trouvé : {file_path}")

        # Charger les données
        logger.info("📊 Chargement des données historiques...")
        df = pd.read_csv(
            file_path,
            delimiter=";",
            encoding="utf-8",
            low_memory=False
        )

        # Préparer les données
        logger.info("🔄 Préparation des données pour l'import...")
        records = []
        for _, row in df.iterrows():
            record = {
                'codgeo': row['CODGEO'],
                'pop_1968': float(row['D68_POP']) if 'D68_POP' in row and pd.notna(row['D68_POP']) else None,
                'pop_1975': float(row['D75_POP']) if 'D75_POP' in row and pd.notna(row['D75_POP']) else None,
                'pop_1982': float(row['D82_POP']) if 'D82_POP' in row and pd.notna(row['D82_POP']) else None,
                'pop_1990': float(row['D90_POP']) if 'D90_POP' in row and pd.notna(row['D90_POP']) else None,
                'pop_1999': float(row['D99_POP']) if 'D99_POP' in row and pd.notna(row['D99_POP']) else None,
                'pop_2010': float(row['P10_POP']) if 'P10_POP' in row and pd.notna(row['P10_POP']) else None,
                'pop_2015': float(row['P15_POP']) if 'P15_POP' in row and pd.notna(row['P15_POP']) else None,
                'pop_2021': float(row['P21_POP']) if 'P21_POP' in row and pd.notna(row['P21_POP']) else None
            }
            records.append(record)

        # Insérer les données en utilisant SQLAlchemy
        logger.info("💾 Insertion des données en base...")
        session = SessionLocal()
        try:
            # Option 1: Insertion par lots avec bulk_save_objects
            historical_objects = [Historical(**record) for record in records]
            session.bulk_save_objects(historical_objects)
            session.commit()

            # Option 2: Alternative avec bulk_insert_mappings
            # session.bulk_insert_mappings(Historical, records)
            # session.commit()

            logger.info(f"✨ Import terminé avec succès : {len(records)} enregistrements importés")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erreur lors de l'insertion des données : {str(e)}")
            raise
        finally:
            session.close()

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation : {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données historiques")
    import_historical_data()
    logger.info("🏁 Import terminé")
