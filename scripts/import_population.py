import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:5456CopaS@localhost:5432/myapi_db"
engine = create_engine(DATABASE_URL)

def clean_database():
    """Nettoie la table populations avant l'import"""
    try:
        with engine.connect() as conn:
            logger.info("🗑️ Nettoyage de la table populations...")
            conn.execute("TRUNCATE TABLE populations RESTART IDENTITY CASCADE")
            logger.info("✅ Table nettoyée avec succès")
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

        logger.info(f"📊 Chargement des données depuis {file_path}...")

        # Charger le CSV en chunks pour éviter les problèmes de mémoire
        chunk_size = 100000  # Ajuster selon la mémoire disponible
        chunk_iter = pd.read_csv(
            file_path,
            delimiter=";",
            encoding="utf-8",
            low_memory=False,
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

            # Préparer les données pour l'insertion
            records = []
            for _, row in df.iterrows():
                record = {
                  'nivgeo': str(row['NIVGEO']),
                  'codgeo': str(row['CODGEO']),
                  'libgeo': str(row['LIBGEO']),
                  'sexe': str(row['SEXE']),  # Assurer que c'est bien une chaîne
                  'aged100': str(row['AGED100']).zfill(3),  # Formater avec des zéros (ex: 0 -> 000, 1 -> 001)
                  'nb': float(row['NB']) if pd.notna(row['NB']) else 0.0
                }
                records.append(record)

            # Insérer les données en base
            with engine.connect() as conn:
                for record in records:
                    conn.execute("""
                        INSERT INTO populations
                        (nivgeo, codgeo, libgeo, sexe, aged100, nb)
                        VALUES
                        (%(nivgeo)s, %(codgeo)s, %(libgeo)s, %(sexe)s, %(aged100)s, %(nb)s)
                    """, record)

            total_records += len(records)
            logger.info(f"✅ Importé {len(records)} enregistrements dans le chunk {chunk_index + 1}")

        logger.info(f"✨ Import terminé avec succès : {total_records} enregistrements importés")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import_population_data()
