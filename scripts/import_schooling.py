import os
import pandas as pd
import psycopg2
from io import StringIO

# Configuration
DATA_PATH = "data/education/schooling"
YEARS = [2017, 2018, 2019, 2020, 2021]
DB_CONFIG = {
    'host': 'localhost',
    'database': 'myapi_db',
    'user': 'postgres',
    'password': '5456CopaS'
}

# Taille optimale du chunk pour un import rapide
CHUNK_SIZE = 50000

def optimize_db_settings(cur):
    """Optimise les paramètres de la base de données pour un import rapide."""
    print("⚙️ Optimisation des paramètres de la base de données...")
    cur.execute("SET work_mem = '512MB';")
    cur.execute("SET maintenance_work_mem = '512MB';")
    cur.execute("SET synchronous_commit = off;")

def prepare_table_for_import(cur):
    """Prépare la table pour un import massif plus rapide."""
    print("⚙️ Préparation de la table pour l'import...")
    cur.execute("ALTER TABLE schooling SET UNLOGGED;")
    cur.execute("DROP INDEX IF EXISTS ix_schooling_geo_code;")
    cur.execute("DROP INDEX IF EXISTS ix_schooling_year;")
    cur.execute("ALTER TABLE schooling DISABLE TRIGGER ALL;")

def restore_table_settings(cur):
    """Restaure les paramètres normaux de la table après import."""
    print("⚙️ Restauration des paramètres de la table...")
    cur.execute("ALTER TABLE schooling SET LOGGED;")
    cur.execute("CREATE INDEX ix_schooling_geo_code ON schooling(geo_code);")
    cur.execute("CREATE INDEX ix_schooling_year ON schooling(year);")
    cur.execute("ALTER TABLE schooling ENABLE TRIGGER ALL;")

def clean_schooling_table(cur):
    """Nettoie rapidement la table avec TRUNCATE au lieu de DELETE."""
    print("🗑️ Nettoyage de la table schooling...")
    cur.execute("TRUNCATE TABLE schooling RESTART IDENTITY;")

def import_schooling_data():
    """Importe les données de scolarisation en mode optimisé."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False  # Désactiver l'autocommit pour booster la vitesse
    cur = conn.cursor()

    try:
        # Optimisation des paramètres
        optimize_db_settings(cur)
        prepare_table_for_import(cur)

        # Nettoyage rapide de la table
        clean_schooling_table(cur)
        conn.commit()

        total_imported = 0

        for year in YEARS:
            file_path = os.path.join(DATA_PATH, f"TD_FOR1_{year}.csv")
            if not os.path.exists(file_path):
                print(f"❌ Fichier introuvable : {file_path}")
                continue

            print(f"📥 Importing {file_path}...")

            for chunk_index, df in enumerate(pd.read_csv(file_path,
                               sep=";",
                               dtype={"CODGEO": str, "AGEFORD": str, "SEXE": str, "ILETUR": str, "NB": str},
                               chunksize=CHUNK_SIZE)):

                print(f"🔎 Chunk {chunk_index + 1} - Colonnes détectées : {df.columns.tolist()}")

                # Nettoyage des données avant import
                df['AGEFORD'] = df['AGEFORD'].astype(str).str.zfill(3)  # S'assurer que les âges sont bien en 3 caractères
                df['SEXE'] = df['SEXE'].astype(str)
                df['ILETUR'] = df['ILETUR'].astype(str).str.strip()

                # Vérifier que `NB` est bien un float et remplacer `NaN` par `0.0`
                df['NB'] = pd.to_numeric(df['NB'], errors='coerce').fillna(0.0)

                # Garder uniquement les valeurs autorisées pour `ILETUR`
                valid_values = {"Z", "1", "2", "3", "4", "5"}
                df['ILETUR'] = df['ILETUR'].apply(lambda x: x if x in valid_values else "Z")

                # Vérification des valeurs incorrectes avant import
                invalid_values = df[~df['ILETUR'].isin(valid_values)]
                if not invalid_values.empty:
                    print(f"⚠️ Chunk {chunk_index + 1} - Valeurs incorrectes détectées :")
                    print(invalid_values['ILETUR'].value_counts())

                # Création d'un buffer optimisé
                output = StringIO()
                df.apply(
                    lambda x: output.write(
                        f"{x['CODGEO']}\t{year}\t{x['AGEFORD']}\t{x['SEXE']}\t{x['ILETUR']}\t{x['NB']}\tNOW()\tNOW()\n"
                    ),
                    axis=1
                )
                output.seek(0)

                # COPY pour un import optimisé dans PostgreSQL
                cur.copy_from(output, 'schooling',
                              columns=('geo_code', 'year', 'age', 'sex', 'education_status', 'number', 'created_at', 'updated_at'),
                              sep='\t')

                conn.commit()
                rows_imported = cur.rowcount
                total_imported += rows_imported

            print(f"✅ Importé {total_imported} enregistrements pour {year}")

        # Restaurer les paramètres normaux
        restore_table_settings(cur)
        conn.commit()

        print(f"✨ Import terminé. Total importé : {total_imported} enregistrements")

    except Exception as e:
        print(f"❌ Erreur lors de l'importation : {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import_schooling_data()
