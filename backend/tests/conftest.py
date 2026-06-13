import os

from cryptography.fernet import Fernet

# Must be set BEFORE importing any app module that reads settings
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test_secret_key_minimum_32_characters_here_ok")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("TOTP_ISSUER", "GestionMailsTest")

import pytest
import pyotp
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import hash_password, generate_totp_secret
from app.models.user import User

# Import all models so they are registered with Base.metadata before create_all
from app.models.order import Orden, ExcelUpload
from app.models.audit import AuditEvent, DJTemplate

# SQLite in-memory engine shared across the test session
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)


# Enable foreign key enforcement in SQLite (disabled by default)
@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestingSessionLocal = sessionmaker(_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables once per test session, drop them at the end."""
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db(setup_test_database):
    """
    Provide a transactional session for each test.
    Changes are rolled back after each test so tests don't pollute each other.
    """
    session = _TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def client(db):
    """FastAPI TestClient with the test DB session injected."""
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """
    Create a test user with a unique username and TOTP secret.
    Returns (user, totp_secret) so callers can generate valid TOTP codes.
    """
    totp_secret = generate_totp_secret()
    user = User(
        username=f"test_{os.urandom(4).hex()}",
        hashed_password=hash_password("SecurePass123!"),
        totp_secret=totp_secret,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user, totp_secret


@pytest.fixture
def auth_headers(client, test_user):
    """
    Perform full login + TOTP verification and return Authorization headers.
    Depends on client (which injects db) and test_user (created in same db session).
    """
    user, totp_secret = test_user
    r = client.post(
        "/auth/login",
        json={"username": user.username, "password": "SecurePass123!"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    pending_token = r.json()["pending_token"]

    code = pyotp.TOTP(totp_secret).now()
    r = client.post(
        "/auth/verify-totp",
        json={"pending_token": pending_token, "code": code},
    )
    assert r.status_code == 200, f"TOTP verification failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
