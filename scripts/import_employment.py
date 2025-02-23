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

def clean_float(val):
    """Nettoie les valeurs float, remplace NaN par None"""
    if pd.isna(val):
        return None
    return float(val)

def clean_database():
    """Nettoie la table employment avant l'import"""
    try:
        with engine.connect() as conn:
            logger.info("🗑️ Nettoyage de la table employment...")
            conn.execute("TRUNCATE TABLE employment RESTART IDENTITY CASCADE")
            logger.info("✅ Table nettoyée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def verify_files():
    """Vérifie que les fichiers nécessaires existent"""
    files = {
        'active': Path("data/employment/activity/base-cc-emploi-pop-active-2021.CSV"),
        'characteristics': Path("data/employment/characteristics/base-cc-caract_emp-2021.CSV")
    }

    for name, path in files.items():
        if not path.exists():
            raise FileNotFoundError(f"❌ Fichier {name} non trouvé : {path}")
        logger.info(f"✅ Fichier {name} trouvé : {path}")

def import_employment_data():
    """Importe les données d'emploi depuis les fichiers CSV"""
    try:
        # Vérifier les fichiers
        verify_files()

        # Nettoyer la base de données
        clean_database()

        # Charger les données actives
        logger.info("📊 Chargement des données de population active...")
        active_df = pd.read_csv(
            Path("data/employment/activity/base-cc-emploi-pop-active-2021.CSV"),
            delimiter=";",
            encoding="utf-8",
            dtype={"CODGEO": str}
        )

        # Charger les données des caractéristiques
        logger.info("📊 Chargement des données de caractéristiques d'emploi...")
        caract_df = pd.read_csv(
            Path("data/employment/characteristics/base-cc-caract_emp-2021.CSV"),
            delimiter=";",
            encoding="utf-8",
            dtype={"CODGEO": str}
        )

        # Préparer les données pour l'import
        logger.info("🔄 Préparation des données pour l'import...")
        records = []
        for _, row in active_df.iterrows():
            caract_row = caract_df[caract_df['CODGEO'] == row['CODGEO']].iloc[0] if not caract_df[caract_df['CODGEO'] == row['CODGEO']].empty else None

            record = {
                'geo_code': row['CODGEO'],
                'year': 2021,
                'women_15_64': clean_float(row['P21_F1564']),
                'women_active_15_64': clean_float(row['P21_FACT1564']),
                'women_employed_15_64': clean_float(row['P21_FACTOCC1564']),
                'women_employees_25_54': clean_float(caract_row['P21_FSAL2554']) if caract_row is not None else None,
                'women_part_time_25_54': clean_float(caract_row['P21_FSAL2554_TP']) if caract_row is not None else None,
                'women_employees_15_64': clean_float(caract_row['P21_FSAL1564']) if caract_row is not None else None,
                'women_part_time_15_64': clean_float(caract_row['P21_FSAL1564_TP']) if caract_row is not None else None
            }
            records.append(record)

        # Insérer les données
        logger.info("💾 Insertion des données en base...")
        with engine.connect() as conn:
            for record in records:
                conn.execute("""
                    INSERT INTO employment (
                        geo_code, year,
                        women_15_64, women_active_15_64, women_employed_15_64,
                        women_employees_25_54, women_part_time_25_54,
                        women_employees_15_64, women_part_time_15_64
                    ) VALUES (
                        %(geo_code)s, %(year)s,
                        %(women_15_64)s, %(women_active_15_64)s, %(women_employed_15_64)s,
                        %(women_employees_25_54)s, %(women_part_time_25_54)s,
                        %(women_employees_15_64)s, %(women_part_time_15_64)s
                    )
                """, record)

        logger.info(f"✨ Import terminé avec succès : {len(records)} enregistrements importés")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation : {str(e)}")
        raise

if __name__ == "__main__":
    import_employment_data()
