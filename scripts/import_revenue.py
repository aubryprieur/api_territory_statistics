import sys
import os
import pandas as pd
from sqlalchemy import text
from pathlib import Path
import logging
import traceback

# Ajouter le répertoire racine du projet au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des modules app
from app.database import engine, SessionLocal
from app.models import Revenue

def clean_float(val):
    """Nettoie les valeurs float, remplace NaN par None"""
    if pd.isna(val):
        return None
    if isinstance(val, str):
        # Remplacer les virgules par des points
        val = val.replace(',', '.')
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def clean_geo_code(code):
    """Nettoie les codes géographiques (supprime .0, etc.)"""
    if pd.isna(code):
        return None
    # Convertir en string
    code_str = str(code)
    # Supprimer le .0 à la fin si présent
    if code_str.endswith('.0'):
        code_str = code_str[:-2]
    return code_str

def clean_database():
    """Nettoie la table revenues avant l'import"""
    try:
        with engine.connect() as conn:
            logger.info("🗑️ Nettoyage de la table revenues...")
            conn.execute(text("TRUNCATE TABLE revenues RESTART IDENTITY CASCADE"))
            logger.info("✅ Table nettoyée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def get_file_suffix(level):
    """Renvoie le suffixe correct pour le niveau géographique"""
    suffixes = {
        'commune': 'COM',    # COM et non COMMUNE
        'epci': 'EPCI',
        'department': 'DEP', # DEP et non DEPARTMENT
        'region': 'REG',     # REG et non REGION
        'france': 'METRO'    # METRO pour la France
    }
    return suffixes.get(level, level.upper())

def import_data_for_level(level, years):
    """Importe les données pour un niveau géographique spécifique"""
    logger.info(f"📊 Importation des données pour le niveau: {level}")

    # Obtenir le suffixe correct pour le fichier
    file_suffix = get_file_suffix(level)

    for year in years:
        year_suffix = str(year)[2:]

        # Construire le chemin du fichier avec le suffixe correct
        file_path = Path(f"data/revenues/{level}/cc_filosofi_{year}_{file_suffix}.csv")

        if not file_path.exists():
            logger.warning(f"⚠️ Fichier non trouvé: {file_path}")
            continue

        logger.info(f"🔄 Traitement du fichier {file_path}...")

        try:
            # Charger le fichier CSV
            df = pd.read_csv(
                file_path,
                delimiter=";",
                encoding="utf-8",
                low_memory=False
            )

            # Déterminer les noms de colonnes pour les revenus médians et les taux de pauvreté
            median_col = f"MED{year_suffix}"
            poverty_col = f"TP60{year_suffix}"

            # Vérifier si les colonnes existent
            if median_col not in df.columns or poverty_col not in df.columns:
                logger.warning(f"⚠️ Colonnes manquantes dans le fichier {file_path}: {median_col}, {poverty_col}")
                continue

            # Préparer les données pour l'insertion
            records = []
            for _, row in df.iterrows():
                # Déterminer le code géographique
                if level == 'france':
                    geo_code = 'FR'
                else:
                    # Nettoyer le code géographique (supprimer .0, etc.)
                    geo_code = clean_geo_code(row['CODGEO'])

                record = {
                    'geo_type': level,
                    'geo_code': geo_code,
                    'year': year,
                    'median_revenue': clean_float(row[median_col]),
                    'poverty_rate': clean_float(row[poverty_col])
                }
                records.append(record)

            # Insérer les données en base
            session = SessionLocal()
            try:
                # Utiliser bulk_insert_mappings pour une meilleure performance
                if records:
                    # Insérer par lots pour les grands volumes de données
                    batch_size = 5000
                    for i in range(0, len(records), batch_size):
                        batch = records[i:i+batch_size]
                        session.bulk_insert_mappings(Revenue, batch)
                        session.commit()
                        logger.info(f"  - {min(i+batch_size, len(records))}/{len(records)} enregistrements traités")

                logger.info(f"✅ Importé {len(records)} enregistrements pour {level}, année {year}")
            except Exception as e:
                session.rollback()
                logger.error(f"❌ Erreur lors de l'importation des données {level} pour {year}: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                session.close()

        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement du fichier {level} pour {year}: {str(e)}")
            logger.error(traceback.format_exc())

def import_revenue_data():
    """Fonction principale d'importation des données de revenus"""
    try:
        # Nettoyage de la base
        clean_database()

        # Années à traiter
        years = range(2017, 2022)

        # Niveaux géographiques à traiter
        levels = ['commune', 'epci', 'department', 'region', 'france']

        # Importer les données pour chaque niveau
        for level in levels:
            import_data_for_level(level, years)

        logger.info("✨ Importation des données de revenus terminée avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur générale lors de l'importation: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de revenus")
    import_revenue_data()
    logger.info("🏁 Import terminé")
