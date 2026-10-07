"""
Change le mot de passe d'un utilisateur de l'API (table users).

Le mot de passe est demandé au clavier (il n'apparaît ni à l'écran ni dans l'historique du shell)
et seul son hash bcrypt est enregistré, comme dans app/security.py.

Usage :
    export DATABASE_URL=$(heroku config:get DATABASE_URL -a api-population-france)
    python scripts/set_user_password.py --username aubry
    unset DATABASE_URL

Dépendances : sqlalchemy, psycopg2, python-dotenv, passlib[bcrypt] (bcrypt==4.0.1).
"""
import argparse
import getpass
import os
import sys

from passlib.context import CryptContext
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # identique à app/security.py
MIN_LENGTH = 16

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Changer le mot de passe d'un utilisateur de l'API")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()

    password = getpass.getpass(f"Nouveau mot de passe pour {args.username} : ")
    if len(password) < MIN_LENGTH:
        sys.exit(f"❌ Mot de passe trop court (minimum {MIN_LENGTH} caractères).")
    if getpass.getpass("Confirmer : ") != password:
        sys.exit("❌ Les deux saisies diffèrent.")

    hashed = pwd_context.hash(password)
    assert pwd_context.verify(password, hashed)
    with engine.begin() as conn:
        result = conn.execute(text("UPDATE users SET hashed_password = :h WHERE username = :u"),
                              {"h": hashed, "u": args.username})
    if result.rowcount != 1:
        sys.exit(f"❌ Utilisateur {args.username} introuvable : rien n'a été modifié.")
    print(f"✅ Mot de passe de {args.username} modifié ({engine.url.host}).")
