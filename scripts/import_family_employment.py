import os
import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import logging
import sys

# Ajouter le répertoire parent pour l'import des modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:5456CopaS@localhost:5432/myapi_db"
engine = create_engine(DATABASE_URL)

def clean_database():
    """Nettoie la table family_employment avant l'import"""
    try:
        with engine.connect() as conn:
            logger.info("🗑️ Nettoyage de la table family_employment...")
            conn.execute("TRUNCATE TABLE family_employment RESTART IDENTITY CASCADE")
            logger.info("✅ Table nettoyée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def import_data(year, file_path):
    """Importe les données d'un fichier CSV pour une année spécifique"""
    try:
        logger.info(f"📊 Chargement des données pour {year} depuis {file_path}...")

        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            logger.error(f"❌ Fichier non trouvé: {file_path}")
            return 0

        # Charger le fichier CSV
        df = pd.read_csv(
            file_path,
            delimiter=";",
            encoding="utf-8",
            dtype={"CODGEO": str, "AGEFOR5": int, "TF12": int, "NB": float}
        )

        logger.info(f"📈 Données chargées: {len(df)} lignes")

        # Vérifier que les colonnes nécessaires sont présentes
        required_columns = ["CODGEO", "AGEFOR5", "TF12", "NB"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"❌ Colonnes manquantes dans le fichier: {missing_columns}")
            return 0

        # Nettoyage des données
        df = df.dropna(subset=required_columns)
        logger.info(f"🧹 Après nettoyage: {len(df)} lignes valides")

        # Insertion par lots (batch) pour de meilleures performances
        batch_size = 5000
        total_records = 0

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            records = []

            for _, row in batch.iterrows():
                record = {
                    'geo_code': str(row["CODGEO"]),
                    'year': year,
                    'age_group': int(row["AGEFOR5"]),
                    'tf12': int(row["TF12"]),
                    'number': float(row["NB"])
                }
                records.append(record)

            # Insérer le lot en base
            with engine.begin() as conn:  # Transaction automatique
                conn.execute(
                    """
                    INSERT INTO family_employment
                    (geo_code, year, age_group, tf12, number)
                    VALUES (%(geo_code)s, %(year)s, %(age_group)s, %(tf12)s, %(number)s)
                    """,
                    records
                )

            total_records += len(records)
            logger.info(f"🔄 Progression: {total_records}/{len(df)} enregistrements insérés")

        logger.info(f"✅ Importé {total_records} enregistrements pour {year}")
        return total_records

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation des données pour {year}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def import_family_employment_data():
    """Fonction principale d'importation des données d'emploi des familles"""
    try:
        # Nettoyer la base avant import
        clean_database()

        # Configuration des années et fichiers disponibles
        data_path = Path("data/families/family_employment")

        # Construction d'un dictionnaire dynamique des années disponibles
        available_data = {}

        # Chercher les fichiers existants qui suivent le format TD_FAM6v2_YYYY.csv
        for file_path in data_path.glob("TD_FAM6v2_*.csv"):
            try:
                # Extraire l'année du nom de fichier
                year_str = file_path.stem.split('_')[-1]
                year = int(year_str)
                available_data[year] = file_path
                logger.info(f"📁 Trouvé fichier pour l'année {year}: {file_path}")
            except (ValueError, IndexError):
                logger.warning(f"⚠️ Format de nom de fichier non reconnu: {file_path}")

        if not available_data:
            logger.error("❌ Aucun fichier de données trouvé")
            return

        # Importer chaque année disponible
        total_imported = 0
        for year, file_path in sorted(available_data.items()):
            count = import_data(year, file_path)
            total_imported += count

        logger.info(f"✨ Import terminé. Total: {total_imported} enregistrements pour {len(available_data)} années")

    except Exception as e:
        logger.error(f"❌ Erreur générale lors de l'importation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données d'emploi des familles")
    import_family_employment_data()
    logger.info("🏁 Import terminé")
