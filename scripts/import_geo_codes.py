import sys
import os
import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app
from app.database import SessionLocal
from app.models import GeoCode

# Chemin du fichier CSV
CSV_FILE = "data/geography/COG_au_01-01-2024.csv"

def normalize_geo_code(code):
    """Normalise un code géographique au format standard INSEE (5 chiffres)"""
    if not code or not pd.notna(code):
        return None
    return str(code).zfill(5)

def clean_str(value):
    """ Nettoie et retourne une chaîne de caractères ou None si invalide. """
    return str(value).strip() if pd.notna(value) else None

def clean_geo_codes_table():
    """Nettoie la table geo_codes en supprimant toutes les données."""
    db: Session = SessionLocal()
    try:
        logger.info("🗑️ Nettoyage de la table geo_codes...")
        # Supprimer toutes les données de la table
        deleted_count = db.query(GeoCode).delete()
        db.commit()
        logger.info(f"✅ {deleted_count} enregistrements supprimés de la table geo_codes")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        db.rollback()
    finally:
        db.close()

def import_geo_codes():
    # Nettoyer la table avant l'import
    clean_geo_codes_table()
    db: Session = SessionLocal()
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"❌ Fichier introuvable : {CSV_FILE}")
            return

        logger.info(f"📥 Importing {CSV_FILE}...")

        # Charger le CSV en DataFrame
        df = pd.read_csv(CSV_FILE, sep=";", dtype=str, engine="python")
        df.columns = df.columns.str.strip()  # Supprimer les espaces invisibles
        logger.info(f"📌 Colonnes après correction : {df.columns.tolist()}")  # Vérifier les colonnes

        # Vérification des colonnes attendues
        expected_cols = ["CODGEO", "LIBGEO", "EPCI", "LIBEPCI", "DEP", "REG"]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"⚠️ Colonnes absentes dans le fichier : {missing_cols}")
            return

        # Renommage des colonnes pour correspondre au modèle
        df = df.rename(columns={
            "CODGEO": "codgeo",
            "LIBGEO": "libgeo",
            "EPCI": "epci",
            "LIBEPCI": "libepci",
            "DEP": "dep",
            "REG": "reg"
        })

        # Nettoyage et normalisation des données
        df["codgeo"] = df["codgeo"].apply(normalize_geo_code)  # Normaliser à 5 chiffres
        df["libgeo"] = df["libgeo"].apply(clean_str)
        df["epci"] = df["epci"].apply(clean_str)
        df["libepci"] = df["libepci"].apply(clean_str)
        df["dep"] = df["dep"].apply(lambda x: str(x).zfill(2) if pd.notna(x) else None)
        df["reg"] = df["reg"].apply(clean_str)

        # Vérifier et journaliser la distribution des longueurs de codes
        code_lengths = df["codgeo"].str.len().value_counts()
        logger.info(f"📊 Distribution des longueurs de codes : {code_lengths.to_dict()}")

        if 5 not in code_lengths or code_lengths.get(5, 0) != len(df):
            logger.warning("⚠️ Certains codes n'ont pas 5 caractères après normalisation!")

            # Afficher quelques exemples problématiques
            problematic = df[df["codgeo"].str.len() != 5][["codgeo", "libgeo", "dep"]].head(5)
            if not problematic.empty:
                logger.warning(f"⚠️ Exemples de codes problématiques:\n{problematic}")

        # Vérification des valeurs suspectes avant insertion
        logger.info(f"🔍 Exemples de codes pour le département 02: {df[df['dep'] == '02']['codgeo'].head(5).tolist()}")
        logger.info(f"🔍 Exemples de codes pour le département 59: {df[df['dep'] == '59']['codgeo'].head(5).tolist()}")

        # Insérer en base de données avec `bulk_save_objects` pour plus d'efficacité
        geo_entries = [
            GeoCode(**row.dropna().to_dict())  # Exclut les NaN
            for _, row in df.iterrows()
        ]

        # Insertion par lots pour économiser la mémoire
        batch_size = 1000
        for i in range(0, len(geo_entries), batch_size):
            batch = geo_entries[i:i+batch_size]
            db.bulk_save_objects(batch)
            db.commit()
            logger.info(f"  - Progression: {min(i+batch_size, len(geo_entries))}/{len(geo_entries)} enregistrements")

        logger.info(f"✅ Imported {len(geo_entries)} rows.")

        # Vérifier après import
        db.commit()  # Assurez-vous que toutes les données sont persistées
        count_5_digits = db.query(GeoCode).filter(GeoCode.codgeo.like('_____')).count()
        logger.info(f"📊 Après import: {count_5_digits} codes à 5 chiffres sur {len(geo_entries)} total")

    except IntegrityError as e:
        db.rollback()
        logger.error(f"❌ Erreur d'intégrité lors de l'import : {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur générale lors de l'import : {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des codes géographiques")
    import_geo_codes()
    logger.info("🏁 Import terminé")
