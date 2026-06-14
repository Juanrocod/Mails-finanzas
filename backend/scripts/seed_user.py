"""
Usage: python scripts/seed_user.py [username] [password]
Creates the initial Middle Office user and prints the TOTP QR URI.

Run from the backend/ directory with the venv activated:
    python scripts/seed_user.py
    python scripts/seed_user.py middleoffice MyPassword123!
"""
import sys
import os

# Add backend/ to path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password, generate_totp_secret, get_totp_provisioning_uri
from app.core.config import settings
from app.models.user import User


def seed_user(username: str = "middleoffice", password: str = "CambiarEstaPass123!") -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"Usuario '{username}' ya existe. No se creó uno nuevo.")
            return

        totp_secret = generate_totp_secret()
        user = User(
            username=username,
            hashed_password=hash_password(password),
            totp_secret=totp_secret,
            is_active=True,
        )
        db.add(user)
        db.commit()

        uri = get_totp_provisioning_uri(totp_secret, username, settings.TOTP_ISSUER)
        print(f"\n✓ Usuario '{username}' creado exitosamente.")
        print(f"\nEscaneá este URI con Google Authenticator, Authy o cualquier app TOTP:")
        print(f"\n  {uri}")
        print(f"\nO ingresá la clave secreta manualmente:")
        print(f"  Secret: {totp_secret}")
        print(f"\nContemplá cambiar la contraseña inicial: {password}")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "middleoffice"
    password = sys.argv[2] if len(sys.argv) > 2 else "CambiarEstaPass123!"
    seed_user(username, password)
