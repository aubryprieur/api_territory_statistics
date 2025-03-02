import sys
import pandas as pd
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

# Charger les variables d'environnement avant d'importer les modules qui en dépendent
load_dotenv()

# Ajouter le dossier 'app' au chemin d'importation
sys.path.append("app")

from app.database import SessionLocal, engine
from app.models import Birth

def import_csv_to_db():
    print("📥 Chargement des données depuis le fichier CSV...")

    # Charger le fichier CSV
    file_path = "data/births/DS_ETAT_CIVIL_NAIS_COMMUNES_data.csv"
    df = pd.read_csv(file_path, delimiter=";", encoding="utf-8", low_memory=False)

    # Renommer les colonnes pour correspondre aux noms des colonnes de la base
    df = df.rename(columns={
        "GEO": "geo",
        "GEO_OBJECT": "geo_object",
        "TIME_PERIOD": "time_period",
        "OBS_VALUE": "obs_value"
    })

    # Sélectionner uniquement les colonnes nécessaires
    df = df[["geo", "geo_object", "time_period", "obs_value"]]

    # Vérifier les 5 premières lignes
    print(df.head())

    # Connexion à la base de données
    session = SessionLocal()

    try:
        print("🗄️ Insertion des données dans la base PostgreSQL...")
        session.bulk_insert_mappings(Birth, df.to_dict(orient="records"))
        session.commit()
        print("✅ Données importées avec succès dans la table `births` !")
    except Exception as e:
        session.rollback()
        print(f"❌ Erreur lors de l'importation des données : {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import_csv_to_db()
