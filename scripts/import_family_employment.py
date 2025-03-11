import os
import pandas as pd
import psycopg2
from sqlalchemy import text
from pathlib import Path
import logging
import sys
from io import StringIO
import traceback

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des objets depuis app.database
from app.database import engine
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Obtenir l'URL de la base de données depuis les variables d'environnement
DATABASE_URL = os.environ.get("DATABASE_URL")

# Extraire les paramètres de connexion de l'URL
from urllib.parse import urlparse

parsed_url = urlparse(DATABASE_URL)
DB_CONFIG = {
    "host": parsed_url.hostname,
    "port": parsed_url.port,
    "database": parsed_url.path[1:],
    "user": parsed_url.username,
    "password": parsed_url.password
}

def clean_database():
    """Nettoie la table family_employment avant l'import"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        logger.info("🗑️ Nettoyage de la table family_employment...")
        cur.execute("TRUNCATE TABLE family_employment RESTART IDENTITY CASCADE")
        logger.info("✅ Table nettoyée avec succès")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def optimize_db_settings(cur):
    """Optimise les paramètres de la base de données pour un import rapide."""
    logger.info("⚙️ Optimisation des paramètres de la base de données...")
    cur.execute("SET work_mem = '512MB';")
    cur.execute("SET maintenance_work_mem = '512MB';")
    cur.execute("SET synchronous_commit = off;")

def prepare_table_for_import(cur):
    """Prépare la table pour un import massif plus rapide."""
    logger.info("⚙️ Préparation de la table pour l'import...")
    cur.execute("ALTER TABLE family_employment SET UNLOGGED;")
    cur.execute("DROP INDEX IF EXISTS ix_family_employment_age_group;")
    cur.execute("DROP INDEX IF EXISTS ix_family_employment_geo_code;")
    cur.execute("DROP INDEX IF EXISTS ix_family_employment_tf12;")
    cur.execute("DROP INDEX IF EXISTS ix_family_employment_year;")
    cur.execute("DROP INDEX IF EXISTS ix_family_employment_geo_code_year_age_group_tf12;")
    cur.execute("ALTER TABLE family_employment DISABLE TRIGGER ALL;")

def restore_table_settings(cur):
    """Restaure les paramètres normaux de la table après import."""
    logger.info("⚙️ Restauration des paramètres de la table...")
    cur.execute("ALTER TABLE family_employment SET LOGGED;")
    cur.execute("CREATE INDEX ix_family_employment_age_group ON family_employment(age_group);")
    cur.execute("CREATE INDEX ix_family_employment_geo_code ON family_employment(geo_code);")
    cur.execute("CREATE INDEX ix_family_employment_tf12 ON family_employment(tf12);")
    cur.execute("CREATE INDEX ix_family_employment_year ON family_employment(year);")
    cur.execute("CREATE INDEX ix_family_employment_geo_code_year_age_group_tf12 ON family_employment(geo_code, year, age_group, tf12);")
    cur.execute("ALTER TABLE family_employment ENABLE TRIGGER ALL;")

def import_data(year, file_path):
    """Importe les données d'un fichier CSV pour une année spécifique en utilisant COPY"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False  # Désactiver l'autocommit pour la transaction
    cur = conn.cursor()

    try:
        # Optimisations pour l'import
        optimize_db_settings(cur)
        prepare_table_for_import(cur)

        logger.info(f"📊 Chargement des données pour {year} depuis {file_path}...")

        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            logger.error(f"❌ Fichier non trouvé: {file_path}")
            return 0

        # Charger le fichier CSV en chunks pour économiser la mémoire
        chunk_size = 100000  # Ajuster selon les besoins
        chunks = pd.read_csv(
            file_path,
            delimiter=";",
            encoding="utf-8",
            dtype={"CODGEO": str, "AGEFOR5": str, "TF12": str, "NB": float},
            chunksize=chunk_size
        )

        total_records = 0

        for i, chunk in enumerate(chunks):
            logger.info(f"🔄 Traitement du chunk {i+1}...")

            # Filtrer les données nécessaires et ajouter l'année
            chunk = chunk[["CODGEO", "AGEFOR5", "TF12", "NB"]].dropna()
            chunk["year"] = year

            # Créer un buffer pour COPY
            output = StringIO()
            chunk.apply(
                lambda x: output.write(
                    f"{x['CODGEO']}\t{year}\t{x['AGEFOR5']}\t{x['TF12']}\t{x['NB']}\tNOW()\tNOW()\n"
                ),
                axis=1
            )
            output.seek(0)

            # Utiliser COPY pour un import rapide
            cur.copy_from(
                output,
                'family_employment',
                columns=('geo_code', 'year', 'age_group', 'tf12', 'number', 'created_at', 'updated_at'),
                sep='\t'
            )

            records_in_chunk = len(chunk)
            total_records += records_in_chunk
            logger.info(f"📈 Chunk {i+1}: {records_in_chunk} enregistrements traités")

            # Commit à chaque chunk
            conn.commit()

        # Restaurer les paramètres de table et index après import
        restore_table_settings(cur)
        conn.commit()

        logger.info(f"✅ Importé {total_records} enregistrements pour {year}")
        return total_records

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erreur lors de l'importation des données pour {year}: {str(e)}")
        logger.error(traceback.format_exc())
        return 0
    finally:
        cur.close()
        conn.close()

def import_family_employment_data():
    """Fonction principale d'importation des données d'emploi des familles"""
    try:
        # Nettoyer la base avant import
        clean_database()

        # Configuration des années et fichiers disponibles
        data_path = Path("data/families/family_employment")
        total_imported = 0

        # Chercher les fichiers existants qui suivent le format TD_FAM6v2_YYYY.csv
        for file_path in data_path.glob("TD_FAM6v2_*.csv"):
            try:
                # Extraire l'année du nom de fichier
                year_str = file_path.stem.split('_')[-1]
                year = int(year_str)

                logger.info(f"📁 Traitement du fichier pour l'année {year}: {file_path}")
                count = import_data(year, file_path)
                total_imported += count

            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Format de nom de fichier non reconnu ou erreur: {file_path}, {str(e)}")

        logger.info(f"✨ Import terminé. Total: {total_imported} enregistrements")

    except Exception as e:
        logger.error(f"❌ Erreur générale lors de l'importation: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données d'emploi des familles")
    import_family_employment_data()
    logger.info("🏁 Import terminé")
