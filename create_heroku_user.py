from app.database import SessionLocal
from app.models import User
from app.security import get_password_hash

def create_user():
    db = SessionLocal()
    try:
        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(User).filter(User.username == 'aubry').first()
        if existing_user:
            print('L\'utilisateur aubry existe déjà')
        else:
            # Créer le nouvel utilisateur
            user = User(
                username='aubry',
                email='aubry.prieur@copas.coop',
                hashed_password=get_password_hash('T8$zbGp4Dq!7LmNv5xKe'),
                is_active=True
            )
            db.add(user)
            db.commit()
            print('Utilisateur créé avec succès')
    except Exception as e:
        db.rollback()
        print(f'Erreur: {str(e)}')
    finally:
        db.close()

if __name__ == "__main__":
    create_user()
