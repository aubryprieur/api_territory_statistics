import sys
import os
import pandas as pd
import psycopg2
import logging
from io import StringIO
from sqlalchemy import text
import traceback

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app (pour les opérations qui n'utilisent pas COPY)
from app.database import engine, Base, SessionLocal

# Définition des constantes manquantes
DATA_PATH = "data/education/schooling"
YEARS = [2017, 2018, 2019, 2020, 2021]

# Taille optimale du chunk pour un import rapide
CHUNK_SIZE = 50000

# Récupérer les paramètres de connexion depuis app.database
from sqlalchemy.engine.url import make_url
db_url = engine.url  # objet URL : str() masquerait le mot de passe (SQLAlchemy 2)
DB_CONFIG = {
    'host': db_url.host,
    'port': db_url.port or 5432,
    'database': db_url.database,
    'user': db_url.username,
    'password': db_url.password
}

def optimize_db_settings(cur):
    """Optimise les paramètres de la base de données pour un import rapide."""
    logger.info("⚙️ Optimisation des paramètres de la base de données...")
    cur.execute("SET work_mem = '512MB';")
    cur.execute("SET maintenance_work_mem = '512MB';")
    cur.execute("SET synchronous_commit = off;")

def prepare_table_for_import(cur):
    """Prépare la table pour un import massif plus rapide."""
    logger.info("⚙️ Préparation de la table pour l'import...")
    cur.execute("ALTER TABLE schooling SET UNLOGGED;")
    cur.execute("DROP INDEX IF EXISTS ix_schooling_geo_code;")
    cur.execute("DROP INDEX IF EXISTS ix_schooling_year;")
    cur.execute("ALTER TABLE schooling DISABLE TRIGGER ALL;")

def restore_table_settings(cur):
    """Restaure les paramètres normaux de la table après import."""
    logger.info("⚙️ Restauration des paramètres de la table...")
    cur.execute("ALTER TABLE schooling SET LOGGED;")
    cur.execute("CREATE INDEX ix_schooling_geo_code ON schooling(geo_code);")
    cur.execute("CREATE INDEX ix_schooling_year ON schooling(year);")
    cur.execute("ALTER TABLE schooling ENABLE TRIGGER ALL;")

def clean_schooling_table(cur):
    """Nettoie rapidement la table avec TRUNCATE au lieu de DELETE."""
    logger.info("🗑️ Nettoyage de la table schooling...")
    cur.execute("TRUNCATE TABLE schooling RESTART IDENTITY;")

def verify_files():
    """Vérifie que tous les fichiers nécessaires existent."""
    missing_files = []
    for year in YEARS:
        file_path = os.path.join(DATA_PATH, f"TD_FOR1_{year}.csv")
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        for path in missing_files:
            logger.warning(f"⚠️ Fichier manquant: {path}")
        return False
    return True

def refresh_schooling_summary(cur):
    """Recalcule la table de synthèse schooling_summary (lue par l'API)."""
    logger.info("🧮 Recalcul de schooling_summary...")
    cur.execute("TRUNCATE schooling_summary;")
    cur.execute("""
        INSERT INTO schooling_summary (geo_code, year, total_2y, schooled_2y, total_3_5y, schooled_3_5y)
        SELECT
            geo_code,
            year,
            SUM(CASE WHEN age = '002' THEN number ELSE 0 END),
            SUM(CASE WHEN age = '002' AND education_status IN ('1','2','3','4','5') THEN number ELSE 0 END),
            SUM(CASE WHEN age IN ('003','004','005') THEN number ELSE 0 END),
            SUM(CASE WHEN age IN ('003','004','005') AND education_status IN ('1','2','3','4','5') THEN number ELSE 0 END)
        FROM schooling
        WHERE sex IN ('1','2')
          AND age IN ('002','003','004','005')
        GROUP BY geo_code, year;
    """)
    logger.info(f"✅ schooling_summary : {cur.rowcount} lignes")

def import_schooling_data():
    """Importe les données de scolarisation en mode optimisé."""
    if not verify_files():
        logger.error("❌ Certains fichiers nécessaires sont manquants. Vérifiez le chemin DATA_PATH.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False  # Désactiver l'autocommit pour booster la vitesse
    cur = conn.cursor()

    try:
        # Optimisation des paramètres
        optimize_db_settings(cur)
        prepare_table_for_import(cur)

        # Nettoyage rapide de la table
        clean_schooling_table(cur)
        conn.commit()

        total_imported = 0

        for year in YEARS:
            file_path = os.path.join(DATA_PATH, f"TD_FOR1_{year}.csv")
            logger.info(f"📥 Importing {file_path}...")

            year_total = 0
            for chunk_index, df in enumerate(pd.read_csv(file_path,
                               sep=";",
                               dtype={"CODGEO": str, "AGEFORD": str, "SEXE": str, "ILETUR": str, "NB": str},
                               chunksize=CHUNK_SIZE)):

                logger.info(f"🔎 Chunk {chunk_index + 1} - Traitement de {len(df)} lignes")

                # Nettoyage des données avant import
                df['AGEFORD'] = df['AGEFORD'].astype(str).str.zfill(3)  # S'assurer que les âges sont bien en 3 caractères
                df['SEXE'] = df['SEXE'].astype(str)
                df['ILETUR'] = df['ILETUR'].astype(str).str.strip()

                # Vérifier que `NB` est bien un float et remplacer `NaN` par `0.0`
                df['NB'] = pd.to_numeric(df['NB'], errors='coerce').fillna(0.0)

                # Garder uniquement les valeurs autorisées pour `ILETUR`
                valid_values = {"Z", "1", "2", "3", "4", "5"}
                df['ILETUR'] = df['ILETUR'].apply(lambda x: x if x in valid_values else "Z")

                # Création d'un buffer optimisé
                output = StringIO()
                df.apply(
                    lambda x: output.write(
                        f"{x['CODGEO']}\t{year}\t{x['AGEFORD']}\t{x['SEXE']}\t{x['ILETUR']}\t{x['NB']}\tNOW()\tNOW()\n"
                    ),
                    axis=1
                )
                output.seek(0)

                # COPY pour un import optimisé dans PostgreSQL
                cur.copy_from(output, 'schooling',
                              columns=('geo_code', 'year', 'age', 'sex', 'education_status', 'number', 'created_at', 'updated_at'),
                              sep='\t')

                conn.commit()
                rows_imported = cur.rowcount
                year_total += rows_imported
                logger.info(f"  - Chunk {chunk_index + 1}: {rows_imported} enregistrements insérés")

            total_imported += year_total
            logger.info(f"✅ Importé {year_total} enregistrements pour {year}")

        # Restaurer les paramètres normaux
        restore_table_settings(cur)
        conn.commit()

        # L'API lit schooling_summary : la recalculer après chaque import
        refresh_schooling_summary(cur)
        conn.commit()
        cur.execute("ANALYZE schooling_summary;")
        conn.commit()

        logger.info(f"✨ Import terminé. Total importé : {total_imported} enregistrements")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation : {str(e)}")
        logger.error(traceback.format_exc())
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de scolarisation")
    import_schooling_data()
    logger.info("🏁 Import terminé")
