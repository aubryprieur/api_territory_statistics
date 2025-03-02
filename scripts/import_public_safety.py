import sys
import os
import pandas as pd
from sqlalchemy import text
from pathlib import Path
import logging
import numpy as np
import traceback

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app
from app.database import engine, SessionLocal
from app.models import PublicSafety

def clean_float(val):
    """Nettoie les valeurs float, remplace NaN par 0"""
    if pd.isna(val) or np.isnan(val):
        return 0.0
    return float(val)

def clean_database():
    """Nettoie la table public_safety avant l'import"""
    try:
        with engine.connect() as conn:
            logger.info("🗑️ Nettoyage de la table public_safety...")
            conn.execute(text("TRUNCATE TABLE public_safety RESTART IDENTITY"))
            logger.info("✅ Table nettoyée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def import_commune_data():
    """Importe les données communales depuis le fichier parquet"""
    try:
        df = pd.read_parquet(Path("data/public_safety/commune/donnee-comm-2023.parquet"))

        # Préparation des données
        records = []
        for _, row in df.iterrows():
            if pd.isna(row['CODGEO_2023']) or pd.isna(row['annee']) or pd.isna(row['classe']):
                continue

            records.append({
                'territory_type': 'commune',
                'territory_code': str(row['CODGEO_2023']),
                'year': int(row['annee']),
                'indicator_class': str(row['classe']),
                'rate': clean_float(row['tauxpourmille'])
            })

        # Import en base avec SQLAlchemy ORM
        session = SessionLocal()
        try:
            # Utiliser bulk_insert_mappings pour insérer efficacement par lots
            for i in range(0, len(records), 5000):
                batch = records[i:i+5000]
                session.bulk_insert_mappings(PublicSafety, batch)
                session.commit()
                logger.info(f"🔄 Progression: {min(i+5000, len(records))}/{len(records)} enregistrements communaux insérés")

            logger.info(f"✅ Imported {len(records)} commune records")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error importing commune data: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ Error importing commune data: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def import_department_data():
    """Importe les données départementales"""
    try:
        df = pd.read_csv(
            Path("data/public_safety/department/donnee-dep-2023.csv"),
            sep=';',
            decimal=','
        )

        records = []
        for _, row in df.iterrows():
            if pd.isna(row['Code.département']) or pd.isna(row['annee']) or pd.isna(row['classe']):
                continue

            records.append({
                'territory_type': 'department',
                'territory_code': str(row['Code.département']),
                'year': int(row['annee']),
                'indicator_class': str(row['classe']),
                'rate': clean_float(row['tauxpourmille'])
            })

        # Import en base avec SQLAlchemy ORM
        session = SessionLocal()
        try:
            session.bulk_insert_mappings(PublicSafety, records)
            session.commit()
            logger.info(f"✅ Imported {len(records)} department records")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error importing department data: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ Error importing department data: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def import_region_data():
    """Importe les données régionales"""
    try:
        df = pd.read_csv(
            Path("data/public_safety/region/donnee-reg-2023.csv"),
            sep=';',
            decimal=','
        )

        records = []
        for _, row in df.iterrows():
            if pd.isna(row['Code.région']) or pd.isna(row['annee']) or pd.isna(row['classe']):
                continue

            # Nettoyer le code région (enlever le .0)
            region_code = str(row['Code.région']).replace('.0', '')

            records.append({
                'territory_type': 'region',
                'territory_code': region_code,
                'year': int(row['annee']),
                'indicator_class': str(row['classe']),
                'rate': clean_float(row['tauxpourmille'])
            })

        # Import en base avec SQLAlchemy ORM
        session = SessionLocal()
        try:
            session.bulk_insert_mappings(PublicSafety, records)
            session.commit()
            logger.info(f"✅ Imported {len(records)} region records")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error importing region data: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ Error importing region data: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def main():
    """Fonction principale d'import"""
    try:
        # Vérifier que les fichiers existent
        files = {
            'commune': Path("data/public_safety/commune/donnee-comm-2023.parquet"),
            'department': Path("data/public_safety/department/donnee-dep-2023.csv"),
            'region': Path("data/public_safety/region/donnee-reg-2023.csv")
        }

        for name, path in files.items():
            if not path.exists():
                logger.error(f"❌ File not found: {path}")
                return

        # Nettoyer la base avant import
        clean_database()

        # Importer les données
        import_commune_data()
        import_department_data()
        import_region_data()

        logger.info("✨ All data imported successfully!")

    except Exception as e:
        logger.error(f"❌ Global error during import: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de sécurité publique")
    main()
    logger.info("🏁 Import terminé")
