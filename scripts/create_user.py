import sys
import os
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Charger les variables d'environnement
load_dotenv()

from app.database import SessionLocal
from app.models import User
from app.security import get_password_hash

def create_admin_user(username, email, password):
    db = SessionLocal()
    try:
        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"L'utilisateur {username} existe déjà.")
            return

        # Créer le nouvel utilisateur
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f"✅ Utilisateur {username} créé avec succès!")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la création de l'utilisateur: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Créer un utilisateur administrateur")
    parser.add_argument("--username", required=True, help="Nom d'utilisateur")
    parser.add_argument("--email", required=True, help="Adresse email")
    parser.add_argument("--password", required=True, help="Mot de passe")

    args = parser.parse_args()

    create_admin_user(args.username, args.email, args.password)
