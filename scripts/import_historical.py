import psycopg2
import pandas as pd
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'myapi_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '5456CopaS')
}

def clean_database():
    """Nettoie la table historical s'il le faut"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Vérifier si la table existe
                cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='historical')")
                table_exists = cursor.fetchone()[0]

                if table_exists:
                    logger.info("🗑️ Suppression de la table historical existante...")
                    cursor.execute("DROP TABLE historical CASCADE")
                    logger.info("✅ Table supprimée avec succès")
                else:
                    logger.info("ℹ️ Aucune table historical à supprimer")

                conn.commit()
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la base : {str(e)}")
        raise

def import_historical_data():
    try:
        # Nettoyer la base d'abord
        clean_database()

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

        # Connexion à la base de données
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Créer la table
                logger.info("🔧 Création de la table historical...")
                cursor.execute("""
                    CREATE TABLE historical (
                        id SERIAL PRIMARY KEY,
                        codgeo VARCHAR(10) NOT NULL,
                        pop_1968 FLOAT,
                        pop_1975 FLOAT,
                        pop_1982 FLOAT,
                        pop_1990 FLOAT,
                        pop_1999 FLOAT,
                        pop_2010 FLOAT,
                        pop_2015 FLOAT,
                        pop_2021 FLOAT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                cursor.execute("CREATE INDEX ix_historical_codgeo ON historical(codgeo)")
                logger.info("✅ Table historical créée")

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

                # Insérer les données
                logger.info("💾 Insertion des données en base...")
                for record in records:
                    cursor.execute("""
                        INSERT INTO historical
                        (codgeo, pop_1968, pop_1975, pop_1982, pop_1990, pop_1999, pop_2010, pop_2015, pop_2021)
                        VALUES (%(codgeo)s, %(pop_1968)s, %(pop_1975)s, %(pop_1982)s, %(pop_1990)s, %(pop_1999)s, %(pop_2010)s, %(pop_2015)s, %(pop_2021)s)
                    """, record)

                # Valider les changements
                conn.commit()

                logger.info(f"✨ Import terminé avec succès : {len(records)} enregistrements importés")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation : {str(e)}")
        raise

if __name__ == "__main__":
    import_historical_data()
