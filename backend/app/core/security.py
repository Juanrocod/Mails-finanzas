# backend/app/core/security.py
from datetime import datetime, timedelta, timezone

import bcrypt
import pyotp
from cryptography.fernet import Fernet
from jose import jwt
from sqlalchemy import TypeDecorator, String

UTC = timezone.utc

_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, expires_delta: timedelta) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + expires_delta
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def create_pending_2fa_token(subject: str) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + timedelta(minutes=5)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "pending_2fa"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def create_refresh_token(subject: str) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + timedelta(hours=settings.REFRESH_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict:
    from app.core.config import settings
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def get_totp_provisioning_uri(secret: str, username: str, issuer: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def create_totp_setup_token(user_id: str, invite_token_id: str) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + timedelta(minutes=10)
    return jwt.encode(
        {
            "sub": user_id,
            "invite_token_id": invite_token_id,
            "type": "totp_setup",
            "exp": expire,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


class EncryptedString(TypeDecorator):
    """Fernet symmetric encryption for sensitive DB columns (email, account numbers)."""
    impl = String
    cache_ok = True

    def __init__(self, length: int = 512, **kwargs):
        super().__init__(length, **kwargs)

    _fernet_cache: dict = {}

    def _fernet(self) -> Fernet:
        from app.core.config import settings
        key = settings.ENCRYPTION_KEY
        if key not in EncryptedString._fernet_cache:
            EncryptedString._fernet_cache[key] = Fernet(key.encode())
        return EncryptedString._fernet_cache[key]

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return self._fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self._fernet().decrypt(value.encode()).decode()
