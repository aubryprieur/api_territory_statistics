import pandas as pd
from sqlalchemy import text
from pathlib import Path
import logging
import sys
import os

# Ajouter le répertoire parent au chemin d'import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules de base de données - La fonction load_dotenv() est déjà appelée par app.database
from app.models import Childcare
from app.database import SessionLocal, Base, engine

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration des fichiers source
SOURCE_FILES = {
    'communes_csv_2020': {
        'path': 'data/childcare/commune/alternative/TAUXCOUV2020.csv',
        'type': 'csv',
        'delimiter': ';',
        'encoding': 'utf-8',
        'territory_type': 'commune',
        'year': 2020,
        'data_source': 'csv_2020'
    },
    'communes_csv_2021': {
        'path': 'data/childcare/commune/alternative/TAUXCOUV2021.csv',
        'type': 'csv',
        'delimiter': ';',
        'encoding': 'utf-8',
        'territory_type': 'commune',
        'year': 2021,
        'data_source': 'csv_2021'
    },
    'communes_parquet': {
        'path': 'data/childcare/commune/current/txcouv_pe_com_2017_2022.parquet',
        'type': 'parquet',
        'territory_type': 'commune',
        'data_source': 'parquet'
    },
    'departments_parquet': {
        'path': 'data/childcare/department/txcouv_pe_dep_2017_2022.parquet',
        'type': 'parquet',
        'territory_type': 'department',
        'data_source': 'parquet'
    },
    'epci_parquet': {
        'path': 'data/childcare/epci/txcouv_pe_epci_2017_2022.parquet',
        'type': 'parquet',
        'territory_type': 'epci',
        'data_source': 'parquet'
    },
    'regions_parquet': {
        'path': 'data/childcare/region/txcouv_pe_reg_2017_2022.parquet',
        'type': 'parquet',
        'territory_type': 'region',
        'data_source': 'parquet'
    },
    'france_parquet': {
        'path': 'data/childcare/france/txcouv_pe_nat_2017_2022.parquet',
        'type': 'parquet',
        'territory_type': 'france',
        'data_source': 'parquet'
    }
}

# Mappage des noms de colonnes pour les fichiers CSV
CSV_MAPPING = {
    'csv_2020': {
        'territory_code': 'NUM_COM',
        'territory_name': 'NOM_COM',
        'parent_type': 'epci',
        'parent_code': 'NUM_EPCI',
        'parent_name': 'NOM_EPCI',
        'global_rate': 'tauxcouv_com'
    },
    'csv_2021': {
        'territory_code': 'NUM_COM',
        'territory_name': 'NOM_COM',
        'parent_type': 'epci',
        'parent_code': 'NUM_EPCI',
        'parent_name': 'NOM_EPCI',
        'employment_zone_code': 'NUMZEMPL',
        'employment_zone_name': 'NOMZEMPL',
        'global_rate': 'tauxcouv_com'
    }
}

# Mappage des noms de colonnes pour les fichiers Parquet
PARQUET_MAPPING = {
    'commune': {
        'territory_code': 'numcom',
        'territory_name': 'nomcom',
        'parent_type': 'epci',
        'parent_code': 'numepci',
        'parent_name': 'nomepci',
        'year': 'annee',
        'eaje_psu': 'txcouv_psu_col_com',
        'eaje_hors_psu': 'txcouv_hors_psu_col_com',
        'eaje_total': 'txcouv_eaje_com',
        'preschool': 'txcouv_prescol_com',
        'childminder': 'txcouv_am_ind_com',
        'home_care': 'txcouv_gad_ind_com',
        'individual_total': 'txcouv_ind_com',
        'global_rate': 'txcouv_com'
    },
    'epci': {
        'territory_code': 'numepci',
        'territory_name': 'nomepci',
        'parent_type': 'department',
        'parent_code': 'numdep',
        'parent_name': 'nomdep',
        'year': 'annee',
        'eaje_psu': 'txcouv_psu_col_epci',
        'eaje_hors_psu': 'txcouv_hors_psu_col_epci',
        'eaje_total': 'txcouv_eaje_epci',
        'preschool': 'txcouv_prescol_epci',
        'childminder': 'txcouv_am_ind_epci',
        'home_care': 'txcouv_gad_ind_epci',
        'individual_total': 'txcouv_ind_epci',
        'global_rate': 'txcouv_epci'
    },
    'department': {
        'territory_code': 'numdep',
        'territory_name': 'nomdep',
        'parent_type': 'region',
        'parent_code': 'numregi',
        'parent_name': 'nomregi',
        'year': 'annee',
        'eaje_psu': 'txcouv_psu_col_dep',
        'eaje_hors_psu': 'txcouv_hors_psu_col_dep',
        'eaje_total': 'txcouv_eaje_dep',
        'preschool': 'txcouv_prescol_dep',
        'childminder': 'txcouv_am_ind_dep',
        'home_care': 'txcouv_gad_ind_dep',
        'individual_total': 'txcouv_ind_dep',
        'global_rate': 'txcouv_dep'
    },
    'region': {
        'territory_code': 'numregi',
        'territory_name': 'nomregi',
        'parent_type': None,
        'parent_code': None,
        'parent_name': None,
        'year': 'annee',
        'eaje_psu': 'txcouv_psu_col_reg',
        'eaje_hors_psu': 'txcouv_hors_psu_col_reg',
        'eaje_total': 'txcouv_eaje_reg',
        'preschool': 'txcouv_prescol_reg',
        'childminder': 'txcouv_am_ind_reg',
        'home_care': 'txcouv_gad_ind_reg',
        'individual_total': 'txcouv_ind_reg',
        'global_rate': 'txcouv_reg'
    },
    'france': {
        'territory_code': 'FR',
        'territory_name': 'national',
        'parent_type': None,
        'parent_code': None,
        'parent_name': None,
        'year': 'annee',
        'eaje_psu': 'txcouv_psu_nat',
        'eaje_hors_psu': 'txcouv_hors_psu_col_nat',
        'eaje_total': 'txcouv_eaje_nat',
        'preschool': 'txcouv_prescol_nat',
        'childminder': 'txcouv_am_nat',
        'home_care': 'txcouv_gad_nat',
        'individual_total': 'txcouv_ind_nat',
        'global_rate': 'txcouv_nat'
    }
}

def clean_database():
    """Nettoie la table childcare avant l'import"""
    try:
        with engine.connect() as conn:
            logger.info("🗑️ Nettoyage de la table childcare...")
            conn.execute(text("TRUNCATE TABLE childcare RESTART IDENTITY CASCADE"))
            logger.info("✅ Table nettoyée avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage de la table : {str(e)}")
        raise

def safe_float(value):
    """Convertit une valeur en float de manière sécurisée"""
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (ValueError, TypeError):
        return None

def safe_str(value):
    """Convertit une valeur en string de manière sécurisée"""
    if pd.isna(value):
        return None
    # Convertir en string et supprimer le .0 à la fin si présent (pour les entiers stockés en float)
    value_str = str(value)
    if value_str.endswith('.0'):
        return value_str[:-2]
    return value_str

def import_csv_data(file_config):
    """Importe les données depuis un fichier CSV"""
    try:
        db = SessionLocal()
        file_path = file_config['path']
        territory_type = file_config['territory_type']
        year = file_config.get('year')
        data_source = file_config.get('data_source')

        if not Path(file_path).exists():
            logger.warning(f"⚠️ Fichier non trouvé: {file_path}")
            return 0

        logger.info(f"📊 Importation des données CSV depuis {file_path}...")

        # Charger le CSV
        df = pd.read_csv(
            file_path,
            delimiter=file_config.get('delimiter', ';'),
            encoding=file_config.get('encoding', 'utf-8'),
            low_memory=False
        )

        # Obtenir le mappage approprié
        mapping = CSV_MAPPING.get(data_source, {})

        # Transformation en objets Childcare
        childcare_objects = []
        count = 0

        for _, row in df.iterrows():
            try:
                # Créer un dictionnaire pour les valeurs
                data = {
                    'territory_type': territory_type,
                    'year': year,
                    'data_source': data_source
                }

                # Ajouter les champs mappés
                for model_field, csv_field in mapping.items():
                    if csv_field in row:
                        # Convertir selon le type
                        if model_field in ['eaje_psu', 'eaje_hors_psu', 'eaje_total',
                                          'preschool', 'childminder', 'home_care',
                                          'individual_total', 'global_rate']:
                            data[model_field] = safe_float(row[csv_field])
                        else:
                            data[model_field] = safe_str(row[csv_field])

                # Ajouter l'objet à la liste
                childcare = Childcare(**data)
                childcare_objects.append(childcare)
                count += 1

                # Insérer par lots pour économiser la mémoire
                if len(childcare_objects) >= 1000:
                    db.add_all(childcare_objects)
                    db.commit()
                    childcare_objects = []
                    logger.info(f"🔄 {count} enregistrements CSV traités...")

            except Exception as e:
                logger.error(f"❌ Erreur lors du traitement de la ligne {_}: {str(e)}")
                continue

        # Insérer les objets restants
        if childcare_objects:
            db.add_all(childcare_objects)
            db.commit()

        logger.info(f"✅ Importé {count} enregistrements depuis {file_path}")
        return count

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation des données CSV: {str(e)}")
        db.rollback()
        return 0
    finally:
        db.close()

def import_parquet_data(file_config):
    """Importe les données depuis un fichier Parquet"""
    try:
        db = SessionLocal()
        file_path = file_config['path']
        territory_type = file_config['territory_type']
        data_source = file_config.get('data_source')

        if not Path(file_path).exists():
            logger.warning(f"⚠️ Fichier non trouvé: {file_path}")
            return 0

        logger.info(f"📊 Importation des données Parquet depuis {file_path}...")

        # Charger le fichier Parquet
        df = pd.read_parquet(file_path)

        # Obtenir le mappage approprié
        mapping = PARQUET_MAPPING.get(territory_type, {})

        # Cas spécial pour France où le code est fixe
        if territory_type == 'france':
            df['FR'] = 'FR'  # Ajouter une colonne FR avec la valeur FR

        # Transformation en objets Childcare
        childcare_objects = []
        count = 0

        for _, row in df.iterrows():
            try:
                # Créer un dictionnaire pour les valeurs
                data = {
                    'territory_type': territory_type,
                    'data_source': data_source
                }

                # Ajouter les champs mappés
                for model_field, parquet_field in mapping.items():
                    if isinstance(parquet_field, str) and parquet_field in row:
                        # Convertir selon le type
                        if model_field in ['eaje_psu', 'eaje_hors_psu', 'eaje_total',
                                          'preschool', 'childminder', 'home_care',
                                          'individual_total', 'global_rate']:
                            data[model_field] = safe_float(row[parquet_field])
                        elif model_field == 'year':
                            data[model_field] = int(row[parquet_field])
                        else:
                            data[model_field] = safe_str(row[parquet_field])
                    elif parquet_field is None:
                        data[model_field] = None
                    elif model_field == 'territory_code' and territory_type == 'france':
                        data[model_field] = 'FR'

                # Si la valeur global_rate est None, ne pas insérer
                if data.get('global_rate') is None:
                    continue

                # Ajouter l'objet à la liste
                childcare = Childcare(**data)
                childcare_objects.append(childcare)
                count += 1

                # Insérer par lots pour économiser la mémoire
                if len(childcare_objects) >= 1000:
                    db.add_all(childcare_objects)
                    db.commit()
                    childcare_objects = []
                    logger.info(f"🔄 {count} enregistrements Parquet traités...")

            except Exception as e:
                logger.error(f"❌ Erreur lors du traitement de la ligne Parquet {_}: {str(e)}")
                continue

        # Insérer les objets restants
        if childcare_objects:
            db.add_all(childcare_objects)
            db.commit()

        logger.info(f"✅ Importé {count} enregistrements depuis {file_path}")
        return count

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'importation des données Parquet: {str(e)}")
        db.rollback()
        return 0
    finally:
        db.close()

def main():
    """Fonction principale d'importation"""
    try:
        # Nettoyer la base avant import
        clean_database()

        # Compteur total d'enregistrements importés
        total_count = 0

        # Importer chaque fichier source
        for config_name, file_config in SOURCE_FILES.items():
            file_type = file_config.get('type')

            if file_type == 'csv':
                count = import_csv_data(file_config)
            elif file_type == 'parquet':
                count = import_parquet_data(file_config)
            else:
                logger.warning(f"⚠️ Type de fichier non pris en charge: {file_type}")
                count = 0

            total_count += count

        logger.info(f"✨ Import terminé avec succès! {total_count} enregistrements au total.")

    except Exception as e:
        logger.error(f"❌ Erreur générale lors de l'importation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'import des données de garde d'enfants")
    main()
    logger.info("🏁 Import terminé")
