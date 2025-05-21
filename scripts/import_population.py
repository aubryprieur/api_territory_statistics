import sys
import os
import pandas as pd
import psycopg2
from sqlalchemy import text
from pathlib import Path
import logging
import traceback
from io import StringIO

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app
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

def normalize_geo_code(code):
    """Normalise un code géographique au format standard INSEE (5 chiffres)"""
    if code is None or pd.isna(code):
        return None
    return str(code).zfill(5)

def optimize_db_settings(cur):
    """Optimise les paramètres de la base de données pour un import rapide."""
    logger.info("⚙️ Optimisation des paramètres de la base de données...")
    cur.execute("SET work_mem = '512MB';")
    cur.execute("SET maintenance_work_mem = '512MB';")
    cur.execute("SET synchronous_commit = off;")

def prepare_table_for_import(cur):
    """Prépare la table pour un import massif plus rapide."""
    logger.info("⚙️ Préparation de la table pour l'import...")
    cur.execute("ALTER TABLE populations SET UNLOGGED;")
    cur.execute("DROP INDEX IF EXISTS ix_populations_codgeo;")
    cur.execute("DROP INDEX IF EXISTS ix_populations_codgeo_sexe_aged100;")
    cur.execute("ALTER TABLE populations DISABLE TRIGGER ALL;")

def restore_table_settings(cur):
    """Restaure les paramètres normaux de la table après import."""
    logger.info("⚙️ Restauration des paramètres de la table...")
    cur.execute("ALTER TABLE populations SET LOGGED;")
    cur.execute("CREATE INDEX ix_populations_codgeo ON populations(codgeo);")
    cur.execute("CREATE INDEX ix_populations_codgeo_sexe_aged100 ON populations(codgeo, sexe, aged100);")
    cur.execute("ALTER TABLE populations ENABLE TRIGGER ALL;")

def clean_database():
    """Nettoie la table populations avant l'import"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        logger.info("🗑️ Nettoyage de la table populations...")
        cur.execute("TRUNCATE TABLE populations RESTART IDENTITY CASCADE")
        logger.info("✅ Table nettoyée avec succès")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def import_population_data():
    """Importe les données de population depuis le fichier CSV"""
    try:
        # Nettoyer la base
        clean_database()

        # Charger le fichier CSV
        file_path = Path("data/population/TD_POP1B_2021.csv")
        if not file_path.exists():
            logger.error(f"❌ Fichier non trouvé: {file_path}")
            return

        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False  # Désactiver l'autocommit pour la transaction
        cur = conn.cursor()

        try:
            # Optimisations pour l'import
            optimize_db_settings(cur)
            prepare_table_for_import(cur)

            logger.info(f"📊 Chargement des données depuis {file_path}...")

            # Charger le CSV en chunks pour éviter les problèmes de mémoire
            chunk_size = 200000  # Augmenter pour de meilleures performances, ajuster selon la RAM disponible
            chunk_iter = pd.read_csv(
                file_path,
                delimiter=";",
                encoding="utf-8",
                low_memory=False,
                dtype={"CODGEO": str},  # Assurer que CODGEO est traité comme une chaîne
                chunksize=chunk_size
            )

            total_records = 0

            for chunk_index, df in enumerate(chunk_iter):
                logger.info(f"🔄 Traitement du chunk {chunk_index + 1}...")

                # Vérifier les colonnes attendues
                expected_columns = ["NIVGEO", "CODGEO", "LIBGEO", "SEXE", "AGED100", "NB"]
                missing_columns = [col for col in expected_columns if col not in df.columns]
                if missing_columns:
                    logger.warning(f"⚠️ Colonnes manquantes: {missing_columns}")
                    continue

                # Nettoyer et préparer les données
                df['SEXE'] = df['SEXE'].astype(str)
                df['AGED100'] = df['AGED100'].astype(str).str.zfill(3)  # Garantir 3 chiffres
                df['NB'] = pd.to_numeric(df['NB'], errors='coerce').fillna(0.0)

                # ********* NORMALISATION DES CODES GÉOGRAPHIQUES **********
                # Standardiser tous les codes de communes à 5 chiffres
                df['CODGEO'] = df['CODGEO'].apply(normalize_geo_code)

                # Vérifier et signaler les codes potentiellement problématiques
                code_lengths = df['CODGEO'].str.len().value_counts()
                logger.info(f"📊 Distribution des longueurs de codes géographiques après normalisation: {code_lengths.to_dict()}")

                if len(code_lengths) > 1 or (5 not in code_lengths):
                    logger.warning("⚠️ Certains codes géographiques n'ont pas une longueur de 5 caractères après normalisation!")

                    # Afficher quelques exemples
                    problematic_codes = df[df['CODGEO'].str.len() != 5]['CODGEO'].unique()[:10]
                    if len(problematic_codes) > 0:
                        logger.warning(f"⚠️ Exemples de codes problématiques: {problematic_codes}")
                # ********************************************************

                # Afficher la distribution des premiers chiffres des codes
                first_digits = df['CODGEO'].str[0].value_counts().to_dict()
                logger.info(f"📊 Distribution des premiers chiffres des codes: {first_digits}")

                # Créer un buffer pour COPY
                output = StringIO()
                for _, row in df.iterrows():
                    output.write(f"{row['NIVGEO']}\t{row['CODGEO']}\t{row['LIBGEO']}\t{row['SEXE']}\t{row['AGED100']}\t{row['NB']}\tNOW()\tNOW()\n")
                output.seek(0)

                # Utiliser COPY pour un import rapide
                cur.copy_from(
                    output,
                    'populations',
                    columns=('nivgeo', 'codgeo', 'libgeo', 'sexe', 'aged100', 'nb', 'created_at', 'updated_at'),
                    sep='\t'
                )

                conn.commit()

                rows_imported = cur.rowcount if cur.rowcount > 0 else len(df)
                total_records += rows_imported
                logger.info(f"✅ Chunk {chunk_index + 1}: {rows_imported} enregistrements importés (Total: {total_records})")

            # Restaurer les paramètres normaux et créer les index
            restore_table_settings(cur)
            conn.commit()

            # Vérification finale des données importées
            cur.execute("SELECT SUBSTRING(codgeo, 1, 1) as first_digit, COUNT(*) FROM populations GROUP BY first_digit ORDER BY first_digit")
            result = cur.fetchall()
            logger.info(f"📊 Distribution finale des premiers chiffres des codes en base: {dict(result)}")

            logger.info(f"✨ Import terminé avec succès : {total_records} enregistrements importés")

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur lors de l'importation: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        logger.error(f"❌ Erreur générale lors de l'importation: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de population")
    import_population_data()
    logger.info("🏁 Import terminé")
