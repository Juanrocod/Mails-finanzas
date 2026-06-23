"""
Initializes the dev SQLite DB and creates a default user.
Run from backend/: python scripts/init_dev_db.py
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./dev.db")
os.environ.setdefault("SECRET_KEY", "dev_secret_key_minimum_32_characters_here_change_in_prod")
os.environ.setdefault("ENCRYPTION_KEY", "LyWtB1layYFDFofxU8rPzytOeU9BJYQh6X1tstWHhD4=")
os.environ.setdefault("TOTP_ISSUER", "GestionMails")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ
from app.models.config_filtros import ConfigFiltros
from app.models.invite_token import InviteToken
from app.core.security import hash_password, generate_totp_secret, get_totp_provisioning_uri

engine = create_engine(
    "sqlite:///./dev.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(engine, "connect")
def _fk(dbapi_conn, _):
    dbapi_conn.cursor().execute("PRAGMA foreign_keys=ON")

Base.metadata.create_all(engine)
Session = sessionmaker(engine)
db = Session()

existing = db.query(User).filter_by(username="middleoffice").first()
if existing:
    print("Usuario 'middleoffice' ya existe.")
else:
    secret = generate_totp_secret()
    db.add(User(
        username="middleoffice",
        hashed_password=hash_password("CambiarEstaPass123!"),
        totp_secret=secret,
        is_active=True,
    ))
    db.commit()
    uri = get_totp_provisioning_uri(secret, "middleoffice", "GestionMails")
    print(f"\nUsuario creado exitosamente.")
    print(f"\nEscaneá este URI con Google Authenticator o Authy:")
    print(f"\n  {uri}")
    print(f"\nO ingresa la clave manualmente:")
    print(f"  Secret: {secret}")

db.close()
