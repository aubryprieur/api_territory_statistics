import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import logging
import numpy as np

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:5456CopaS@localhost:5432/myapi_db"
engine = create_engine(DATABASE_URL)

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
            conn.execute("TRUNCATE TABLE public_safety RESTART IDENTITY")
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

            records.append((
                'commune',
                str(row['CODGEO_2023']),
                int(row['annee']),
                str(row['classe']),
                clean_float(row['tauxpourmille'])
            ))

        # Import en base avec la syntaxe correcte
        with engine.connect() as conn:
            conn.execute(
                """
                INSERT INTO public_safety
                (territory_type, territory_code, year, indicator_class, rate)
                VALUES (%s, %s, %s, %s, %s)
                """,
                records
            )

        logger.info(f"✅ Imported {len(records)} commune records")
    except Exception as e:
        logger.error(f"❌ Error importing commune data: {str(e)}")
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

            records.append((
                'department',
                str(row['Code.département']),
                int(row['annee']),
                str(row['classe']),
                clean_float(row['tauxpourmille'])
            ))

        with engine.connect() as conn:
            conn.execute(
                """
                INSERT INTO public_safety
                (territory_type, territory_code, year, indicator_class, rate)
                VALUES (%s, %s, %s, %s, %s)
                """,
                records
            )

        logger.info(f"✅ Imported {len(records)} department records")
    except Exception as e:
        logger.error(f"❌ Error importing department data: {str(e)}")
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

            records.append((
                'region',
                region_code,
                int(row['annee']),
                str(row['classe']),
                clean_float(row['tauxpourmille'])
            ))

        with engine.connect() as conn:
            conn.execute(
                """
                INSERT INTO public_safety
                (territory_type, territory_code, year, indicator_class, rate)
                VALUES (%s, %s, %s, %s, %s)
                """,
                records
            )

        logger.info(f"✅ Imported {len(records)} region records")
    except Exception as e:
        logger.error(f"❌ Error importing region data: {str(e)}")
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

if __name__ == "__main__":
    main()
