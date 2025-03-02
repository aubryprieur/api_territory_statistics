import sys
import os
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy import exists

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app (load_dotenv est déjà appelé par app.database)
from app.database import SessionLocal
from app.models import Family

# Configuration des fichiers et des années
DATA_PATH = "data/families/commune"
YEARS = [2017, 2018, 2019, 2020, 2021]

# Mapping des colonnes correctes
COLUMN_MAPPING = {
    "CODGEO": "geo_code",
    "C{year}_FAM": "total_households",
    "C{year}_COUPAENF": "couples_with_children",
    "C{year}_FAMMONO": "single_parent_families",
    "C{year}_HMONO": "single_fathers",
    "C{year}_FMONO": "single_mothers",
    "C{year}_COUPSENF": "couples_without_children",
    "C{year}_NE24F3": "children_under_24_three_siblings",
    "C{year}_NE24F4P": "children_under_24_four_or_more_siblings",
}

def clean_families_table():
    """Nettoie la table families en supprimant toutes les données."""
    db: Session = SessionLocal()
    try:
        print("🗑️ Nettoyage de la table families...")
        # Supprimer toutes les données de la table
        deleted_count = db.query(Family).delete()
        db.commit()
        print(f"✅ {deleted_count} enregistrements supprimés de la table families")
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        db.rollback()
    finally:
        db.close()

def import_family_data():
    """Importe les données des familles depuis les fichiers CSV."""
    db: Session = SessionLocal()

    try:
        # D'abord, nettoyer la table
        clean_families_table()

        for year in YEARS:
            file_path = os.path.join(DATA_PATH, f"base-cc-coupl-fam-men-{year}.CSV")
            if not os.path.exists(file_path):
                print(f"❌ Fichier introuvable : {file_path}")
                continue

            print(f"📥 Importing {file_path}...")

            # Charger le CSV en DataFrame
            df = pd.read_csv(file_path, sep=";", dtype=str)
            df.columns = df.columns.str.strip()  # Supprimer les espaces invisibles

            # Générer le dictionnaire de renommage avec les colonnes au bon format
            short_year = str(year)[2:]
            rename_dict = {col.format(year=short_year): name for col, name in COLUMN_MAPPING.items()}

            # Vérifier les colonnes manquantes
            missing_columns = [col for col in rename_dict.keys() if col not in df.columns]
            if missing_columns:
                print(f"⚠️ Colonnes absentes dans le fichier {year} : {missing_columns}")
                continue

            # Renommer les colonnes et ajouter l'année
            df = df.rename(columns=rename_dict)
            df["year"] = year

            # Sélectionner uniquement les colonnes utiles
            df = df[list(rename_dict.values()) + ["year"]].dropna(how="all")

            # Convertir les valeurs numériques
            numeric_cols = [col for col in rename_dict.values() if col != "geo_code"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

            # Insérer les données en lot
            records = df.to_dict('records')
            db.bulk_insert_mappings(Family, records)

            db.commit()
            print(f"✅ Importé {len(df)} enregistrements pour {year}")

    except Exception as e:
        print(f"❌ Erreur lors de l'importation : {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_family_data()
