#!/usr/bin/env python
"""
Script pour analyser la structure des fichiers de données de garde d'enfants.
Exécutez-le simplement avec: python scripts/analyze_childcare_files.py
"""
import pandas as pd
import os
from pathlib import Path
import json

# Configuration
FILES_TO_ANALYZE = [
    # CSV communes alternatives
    "data/childcare/commune/alternative/TAUXCOUV2020.csv",
    "data/childcare/commune/alternative/TAUXCOUV2021.csv",
    # Parquet commune
    "data/childcare/commune/current/txcouv_pe_com_2017_2022.parquet",
    # Parquet département
    "data/childcare/department/txcouv_pe_dep_2017_2022.parquet",
    # Parquet EPCI
    "data/childcare/epci/txcouv_pe_epci_2017_2022.parquet",
    # Parquet région
    "data/childcare/region/txcouv_pe_reg_2017_2022.parquet",
    # Parquet France
    "data/childcare/france/txcouv_pe_nat_2017_2022.parquet"
]

def analyze_csv(file_path):
    """Analyse un fichier CSV"""
    print(f"\n\n📊 Analyse du fichier CSV: {file_path}")
    try:
        # Essayer de lire avec différents séparateurs
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(file_path, sep=sep, nrows=5, low_memory=False)
                if len(df.columns) > 1:  # Si on a plus d'une colonne, le séparateur est probablement correct
                    break
            except Exception:
                continue

        # Si on n'a pas réussi à lire correctement, essayer avec détection automatique
        if len(df.columns) <= 1:
            df = pd.read_csv(file_path, sep=None, engine='python', nrows=5)

        # Afficher les informations de base
        print(f"Nombre de colonnes: {len(df.columns)}")
        print(f"Colonnes: {df.columns.tolist()}")

        # Afficher les types de données
        print("\nTypes de données:")
        for col in df.columns:
            print(f"  - {col}: {df[col].dtype}")

        # Afficher les 5 premières lignes
        print("\nEchantillon de données (5 premières lignes):")
        print(df.head().to_string())

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse du fichier CSV: {str(e)}")

def analyze_parquet(file_path):
    """Analyse un fichier Parquet"""
    print(f"\n\n📊 Analyse du fichier Parquet: {file_path}")
    try:
        # Lire le fichier parquet
        df = pd.read_parquet(file_path)

        # Afficher les informations de base
        print(f"Nombre de colonnes: {len(df.columns)}")
        print(f"Colonnes: {df.columns.tolist()}")

        # Afficher les types de données
        print("\nTypes de données:")
        for col in df.columns:
            print(f"  - {col}: {df[col].dtype}")

        # Vérifier les valeurs manquantes
        null_counts = df.isnull().sum()
        print("\nColonnes avec valeurs manquantes:")
        for col, count in null_counts[null_counts > 0].items():
            print(f"  - {col}: {count} valeurs manquantes ({count/len(df)*100:.2f}%)")

        # Afficher les 5 premières lignes
        print("\nEchantillon de données (5 premières lignes):")
        print(df.head().to_string())

        # Afficher quelques statistiques pour les colonnes numériques
        print("\nStatistiques pour les colonnes numériques:")
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            print(df[numeric_cols].describe().to_string())

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse du fichier Parquet: {str(e)}")

def generate_summary():
    """Génère une synthèse comparative des structures de fichiers"""
    print("\n\n📋 SYNTHÈSE COMPARATIVE DES STRUCTURES DE FICHIERS")

    all_columns = set()
    file_structures = {}

    for file_path in FILES_TO_ANALYZE:
        if not Path(file_path).exists():
            print(f"Fichier non trouvé: {file_path}")
            continue

        try:
            if file_path.endswith('.csv'):
                # Pour les CSV
                for sep in [";", ",", "\t"]:
                    try:
                        df = pd.read_csv(file_path, sep=sep, nrows=1)
                        if len(df.columns) > 1:
                            break
                    except:
                        continue
            else:
                # Pour les Parquet
                df = pd.read_parquet(file_path)

            # Enregistrer les colonnes
            columns = df.columns.tolist()
            file_structures[file_path] = columns
            all_columns.update(columns)

        except Exception as e:
            print(f"Erreur lors de l'analyse de {file_path}: {str(e)}")

    # Créer un tableau de comparaison
    all_columns = sorted(list(all_columns))
    comparison_table = {col: [] for col in all_columns}

    for file_path, columns in file_structures.items():
        file_name = Path(file_path).name
        for col in all_columns:
            if col in columns:
                comparison_table[col].append(file_name)

    # Afficher le tableau
    print("\nColonnes présentes dans chaque fichier:")
    for col, files in comparison_table.items():
        print(f"{col}:")
        for file in files:
            print(f"  - {file}")

def main():
    """Fonction principale d'analyse"""
    print("🔍 Analyse des fichiers de données de garde d'enfants...")

    for file_path in FILES_TO_ANALYZE:
        # Vérifier si le fichier existe
        if not Path(file_path).exists():
            print(f"\n❌ Fichier non trouvé: {file_path}")
            continue

        # Analyser le fichier selon son type
        if file_path.endswith('.csv'):
            analyze_csv(file_path)
        elif file_path.endswith('.parquet'):
            analyze_parquet(file_path)
        else:
            print(f"\n⚠️ Type de fichier non pris en charge: {file_path}")

    # Générer une synthèse
    generate_summary()

    print("\n✅ Analyse terminée!")


if __name__ == "__main__":
    main()
