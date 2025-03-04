import os
import sys
from dotenv import load_dotenv

# Ajouter le chemin du projet
sys.path.append(".")

from app.database import SessionLocal
from app.models import User

load_dotenv()

# Connexion à la base de données
db = SessionLocal()

# Vérifier si l'utilisateur existe
user = db.query(User).filter(User.username == "admin").first()
if user:
    print(f"✅ Utilisateur 'admin' trouvé dans la base de données (ID: {user.id})")
else:
    print("❌ Utilisateur 'admin' NON trouvé dans la base de données")

db.close()
