# backend/tests/test_security.py
import os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/gestion_mails_test")
os.environ.setdefault("SECRET_KEY", "test_secret_key_minimum_32_characters_here_ok")
os.environ.setdefault("ENCRYPTION_KEY", "")  # will be replaced below

from cryptography.fernet import Fernet
# Set a valid test encryption key before any imports that load settings
if not os.environ.get("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_totp_secret, verify_totp, get_totp_provisioning_uri,
    EncryptedString,
)
from datetime import timedelta


def test_password_hash_and_verify():
    hashed = hash_password("mysecretpassword")
    assert verify_password("mysecretpassword", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_password_hash_is_different_each_time():
    h1 = hash_password("same_password")
    h2 = hash_password("same_password")
    assert h1 != h2  # bcrypt uses random salt


def test_access_token_round_trip():
    token = create_access_token("user-abc-123", timedelta(hours=1))
    payload = decode_token(token)
    assert payload["sub"] == "user-abc-123"
    assert payload["type"] == "access"


def test_refresh_token_round_trip():
    token = create_refresh_token("user-abc-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-abc-123"
    assert payload["type"] == "refresh"


def test_expired_token_raises():
    from jose import ExpiredSignatureError
    import pytest
    token = create_access_token("user-abc-123", timedelta(seconds=-1))
    with pytest.raises(ExpiredSignatureError):
        decode_token(token)


def test_totp_verify_valid_code():
    import pyotp
    secret = generate_totp_secret()
    valid_code = pyotp.TOTP(secret).now()
    assert verify_totp(secret, valid_code)


def test_totp_verify_invalid_code():
    secret = generate_totp_secret()
    assert not verify_totp(secret, "000000")


def test_totp_provisioning_uri():
    secret = generate_totp_secret()
    uri = get_totp_provisioning_uri(secret, "testuser", "GestionMails")
    assert "otpauth://totp/" in uri
    assert "testuser" in uri
    assert "GestionMails" in uri


def test_encrypted_string_round_trip():
    from sqlalchemy import Column, String, create_engine
    from sqlalchemy.orm import sessionmaker, DeclarativeBase
    from app.core.security import EncryptedString

    class Base(DeclarativeBase):
        pass

    class TestModel(Base):
        __tablename__ = "test_encrypted"
        id = Column(String, primary_key=True)
        secret = Column(EncryptedString(512))

    # Use in-memory SQLite for this unit test (no PostgreSQL needed)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)

    with Session() as session:
        session.add(TestModel(id="1", secret="sensitive_data"))
        session.commit()

    with Session() as session:
        obj = session.get(TestModel, "1")
        assert obj.secret == "sensitive_data"

    # Verify the raw stored value is encrypted (not plaintext)
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT secret FROM test_encrypted WHERE id = '1'"))
        raw = result.fetchone()[0]
        assert raw != "sensitive_data"
        assert len(raw) > 20  # Fernet token is longer than plaintext
