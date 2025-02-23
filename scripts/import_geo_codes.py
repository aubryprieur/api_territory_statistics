import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models import GeoCode

# Chemin du fichier CSV
CSV_FILE = "data/geography/COG_au_01-01-2024.csv"

def clean_str(value):
    """ Nettoie et retourne une chaîne de caractères ou None si invalide. """
    return str(value).strip() if pd.notna(value) else None

def import_geo_codes():
    db: Session = SessionLocal()

    if not os.path.exists(CSV_FILE):
        print(f"❌ Fichier introuvable : {CSV_FILE}")
        return

    print(f"📥 Importing {CSV_FILE}...")

    # Charger le CSV en DataFrame
    df = pd.read_csv(CSV_FILE, sep=";", dtype=str, engine="python")
    df.columns = df.columns.str.strip()  # Supprimer les espaces invisibles
    print("📌 Colonnes après correction :", df.columns.tolist())  # Vérifier les colonnes

    # Vérification des colonnes attendues
    expected_cols = ["CODGEO", "LIBGEO", "EPCI", "LIBEPCI", "DEP", "REG"]
    missing_cols = [col for col in expected_cols if col not in df.columns]
    if missing_cols:
        print(f"⚠️ Colonnes absentes dans le fichier : {missing_cols}")
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

    # Nettoyage des données pour `VARCHAR`
    df["codgeo"] = df["codgeo"].apply(clean_str)
    df["libgeo"] = df["libgeo"].apply(clean_str)
    df["epci"] = df["epci"].apply(clean_str)
    df["libepci"] = df["libepci"].apply(clean_str)
    df["dep"] = df["dep"].apply(clean_str)
    df["reg"] = df["reg"].apply(clean_str)

    # Vérification des valeurs suspectes avant insertion
    print("🔍 Valeurs uniques dans EPCI :", df["epci"].unique()[:10])

    # Insérer en base de données avec `bulk_save_objects` pour plus d'efficacité
    geo_entries = [
        GeoCode(**row.dropna().to_dict())  # Exclut les NaN
        for _, row in df.iterrows()
    ]

    try:
        db.bulk_save_objects(geo_entries)
        db.commit()
        print(f"✅ Imported {len(geo_entries)} rows.")
    except IntegrityError as e:
        db.rollback()
        print(f"❌ Erreur d'intégrité lors de l'import : {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import_geo_codes()
