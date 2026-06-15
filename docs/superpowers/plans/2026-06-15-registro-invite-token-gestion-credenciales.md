# Registro por Invite Token y Gestión de Credenciales — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar registro por invite token de un solo uso, reset de contraseña sin SMTP, cambio de contraseña y TOTP desde la app, y rate limiting en verify-totp y refresh.

**Architecture:** Nueva tabla `invite_tokens` (uno por uso, 48hs TTL). El admin genera tokens via script de consola. El registro es en dos pasos (crear cuenta → confirmar TOTP escaneado) para garantizar que el Authenticator funciona antes de activar la cuenta. Reset de contraseña también por token admin-generado. Cambio de contraseña y regeneración de TOTP requieren autenticación activa.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pyotp + python-jose (backend) · React 18 + TypeScript + qrcode.react + TanStack Query v5 (frontend)

---

## Estructura de archivos

```
backend/
├── app/
│   ├── models/invite_token.py          (NUEVO)
│   ├── schemas/auth.py                 (MODIFICA — 6 schemas nuevos)
│   ├── core/security.py                (MODIFICA — create_totp_setup_token)
│   ├── routers/auth.py                 (MODIFICA — 5 endpoints + 2 rate limits)
│   └── alembic/
│       ├── env.py                      (MODIFICA — importar InviteToken)
│       └── versions/0003_add_invite_tokens.py  (NUEVO)
├── create_invite.py                    (NUEVO — script de consola)
└── tests/
    ├── conftest.py                     (MODIFICA — fixtures invite_token, reset_token)
    ├── test_register.py                (NUEVO)
    └── test_change_credentials.py      (NUEVO)

frontend/
├── src/
│   ├── pages/
│   │   ├── RegisterPage.tsx            (NUEVO)
│   │   └── ResetPasswordPage.tsx       (NUEVO)
│   ├── components/profile/
│   │   ├── ChangePasswordModal.tsx     (NUEVO)
│   │   └── RegenerateTOTPModal.tsx     (NUEVO)
│   ├── services/auth.ts                (MODIFICA — 5 funciones nuevas)
│   ├── components/layout/Sidebar.tsx   (MODIFICA — botones de perfil)
│   └── App.tsx                         (MODIFICA — rutas públicas)
```

---

### Task 1: InviteToken model + migración Alembic + env.py

**Files:**
- Create: `backend/app/models/invite_token.py`
- Create: `backend/alembic/versions/0003_add_invite_tokens.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Crear el modelo SQLAlchemy**

```python
# backend/app/models/invite_token.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class InviteToken(Base):
    __tablename__ = "invite_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)
    tipo = Column(String(10), nullable=False)  # 'invite' | 'reset'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expira_en = Column(DateTime, nullable=False)
    usado_en = Column(DateTime, nullable=True)
    creado_en = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 2: Crear la migración Alembic**

```python
# backend/alembic/versions/0003_add_invite_tokens.py
"""add invite_tokens table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invite_tokens',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('tipo', sa.String(length=10), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('expira_en', sa.DateTime(), nullable=False),
        sa.Column('usado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_invite_tokens_token', 'invite_tokens', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_invite_tokens_token', table_name='invite_tokens')
    op.drop_table('invite_tokens')
```

- [ ] **Step 3: Agregar InviteToken a alembic/env.py**

En `backend/alembic/env.py`, en el bloque de imports de modelos, agregar:

```python
from app.models.invite_token import InviteToken
```

El bloque completo de imports de modelos debe quedar:
```python
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ
from app.models.invite_token import InviteToken
```

- [ ] **Step 4: Aplicar migración a dev.db**

```bash
cd backend
venv\Scripts\alembic upgrade head
```

Resultado esperado:
```
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, add invite_tokens table
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/invite_token.py backend/alembic/versions/0003_add_invite_tokens.py backend/alembic/env.py
git commit -m "feat(backend): InviteToken model and migration 0003"
```

---

### Task 2: Script de consola `create_invite.py`

**Files:**
- Create: `backend/create_invite.py`

- [ ] **Step 1: Escribir el script**

```python
# backend/create_invite.py
"""
Genera links de registro o reset de contraseña.

Uso:
  python create_invite.py invite
  python create_invite.py reset --username <username>
"""
import argparse
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.invite_token import InviteToken
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera invite/reset tokens")
    parser.add_argument("tipo", choices=["invite", "reset"])
    parser.add_argument("--username", help="Username existente (requerido para reset)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user_id = None
        if args.tipo == "reset":
            if not args.username:
                print("Error: --username requerido para tipo 'reset'")
                sys.exit(1)
            user = db.query(User).filter(User.username == args.username).first()
            if not user:
                print(f"Error: usuario '{args.username}' no encontrado en DB")
                sys.exit(1)
            user_id = user.id

        token_value = secrets.token_urlsafe(32)
        expira_en = datetime.now(timezone.utc) + timedelta(hours=48)

        row = InviteToken(
            token=token_value,
            tipo=args.tipo,
            user_id=user_id,
            expira_en=expira_en,
        )
        db.add(row)
        db.commit()

        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        if args.tipo == "invite":
            url = f"{base_url}/register?token={token_value}"
            print(f"\n✓ Link de registro (válido 48hs):\n  {url}\n")
        else:
            url = f"{base_url}/reset-password?token={token_value}"
            print(f"\n✓ Link de reset para '{args.username}' (válido 48hs):\n  {url}\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Probar el script (requiere backend/.env activo)**

```bash
cd backend
venv\Scripts\python create_invite.py invite
```

Resultado esperado (token distinto cada vez):
```
✓ Link de registro (válido 48hs):
  http://localhost:5173/register?token=abc123...
```

- [ ] **Step 3: Probar reset**

```bash
venv\Scripts\python create_invite.py reset --username <usuario_existente_en_dev_db>
```

- [ ] **Step 4: Commit**

```bash
git add backend/create_invite.py
git commit -m "feat(backend): admin script create_invite.py for invite/reset tokens"
```

---

### Task 3: Schemas + security helper

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/core/security.py`

- [ ] **Step 1: Agregar 6 schemas nuevos en auth.py**

El archivo completo debe quedar:

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class PendingTokenResponse(BaseModel):
    pending_token: str
    message: str


class VerifyTOTPRequest(BaseModel):
    pending_token: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ADR-0008: registro e invite tokens
class RegisterRequest(BaseModel):
    token: str
    username: str
    password: str


class RegisterResponse(BaseModel):
    totp_uri: str
    setup_token: str


class ConfirmRegisterRequest(BaseModel):
    setup_token: str
    totp_code: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class RegenerateTOTPRequest(BaseModel):
    totp_code: str


class RegenerateTOTPResponse(BaseModel):
    totp_uri: str
```

- [ ] **Step 2: Agregar create_totp_setup_token en security.py**

Al final de `backend/app/core/security.py`, agregar:

```python
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
```

- [ ] **Step 3: Verificar que los imports existentes no se rompieron**

```bash
cd backend
venv\Scripts\python -c "from app.schemas.auth import RegisterRequest, RegisterResponse, ConfirmRegisterRequest, ResetPasswordRequest, ChangePasswordRequest, RegenerateTOTPRequest, RegenerateTOTPResponse; print('OK')"
venv\Scripts\python -c "from app.core.security import create_totp_setup_token; print('OK')"
```

Ambos deben imprimir `OK`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/core/security.py
git commit -m "feat(backend): auth schemas for register/reset/change-password + create_totp_setup_token"
```

---

### Task 4: POST /auth/register + POST /auth/register/confirm

**Files:**
- Modify: `backend/app/routers/auth.py`

- [ ] **Step 1: Escribir test failing primero**

En `backend/tests/test_register.py`, crear el archivo con los primeros 3 tests:

```python
# backend/tests/test_register.py
import secrets
from datetime import datetime, timedelta, timezone
import pyotp
import pytest

from app.models.invite_token import InviteToken


@pytest.fixture
def invite_token(db):
    token = InviteToken(
        token=secrets.token_urlsafe(32),
        tipo="invite",
        user_id=None,
        expira_en=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(token)
    db.flush()
    return token


@pytest.fixture
def expired_invite_token(db):
    token = InviteToken(
        token=secrets.token_urlsafe(32),
        tipo="invite",
        user_id=None,
        expira_en=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add(token)
    db.flush()
    return token


def test_register_creates_inactive_user(client, invite_token):
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "nuevousuario",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201
    data = r.json()
    assert "totp_uri" in data
    assert "setup_token" in data
    assert data["totp_uri"].startswith("otpauth://totp/")


def test_register_expired_token(client, expired_invite_token):
    r = client.post("/auth/register", json={
        "token": expired_invite_token.token,
        "username": "alguien",
        "password": "SecurePass123!",
    })
    assert r.status_code == 400


def test_register_invalid_token(client):
    r = client.post("/auth/register", json={
        "token": "tokenquenoestaenladb",
        "username": "alguien",
        "password": "SecurePass123!",
    })
    assert r.status_code == 400


def test_register_username_taken(client, invite_token, test_user):
    existing_user, _ = test_user
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": existing_user.username,
        "password": "SecurePass123!",
    })
    assert r.status_code == 409


def test_confirm_register_activates_user(client, invite_token):
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "usuarionuevo2",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201
    setup_token = r.json()["setup_token"]
    totp_uri = r.json()["totp_uri"]
    # extraer secret del URI: otpauth://totp/...?secret=XXXX&...
    secret = totp_uri.split("secret=")[1].split("&")[0]
    code = pyotp.TOTP(secret).now()

    r = client.post("/auth/register/confirm", json={
        "setup_token": setup_token,
        "totp_code": code,
    })
    assert r.status_code == 204


def test_confirm_register_wrong_totp(client, invite_token):
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "usuarionuevo3",
        "password": "SecurePass123!",
    })
    setup_token = r.json()["setup_token"]
    r = client.post("/auth/register/confirm", json={
        "setup_token": setup_token,
        "totp_code": "000000",
    })
    assert r.status_code == 401


def test_confirm_register_invalid_setup_token(client):
    r = client.post("/auth/register/confirm", json={
        "setup_token": "tokeninvalido",
        "totp_code": "123456",
    })
    assert r.status_code == 401


def test_full_registration_then_login(client, invite_token):
    """Flujo completo: registro → confirmar TOTP → login normal."""
    r = client.post("/auth/register", json={
        "token": invite_token.token,
        "username": "usuario_full",
        "password": "SecurePass123!",
    })
    assert r.status_code == 201
    setup_token = r.json()["setup_token"]
    totp_uri = r.json()["totp_uri"]
    secret = totp_uri.split("secret=")[1].split("&")[0]
    code = pyotp.TOTP(secret).now()

    r = client.post("/auth/register/confirm", json={
        "setup_token": setup_token,
        "totp_code": code,
    })
    assert r.status_code == 204

    # login normal
    r = client.post("/auth/login", json={"username": "usuario_full", "password": "SecurePass123!"})
    assert r.status_code == 200
    pending_token = r.json()["pending_token"]

    code = pyotp.TOTP(secret).now()
    r = client.post("/auth/verify-totp", json={"pending_token": pending_token, "code": code})
    assert r.status_code == 200
    assert "access_token" in r.json()
```

- [ ] **Step 2: Correr tests — deben fallar con 404 (endpoints no existen aún)**

```bash
cd backend
venv\Scripts\python -m pytest tests/test_register.py -v
```

Resultado esperado: todos FAIL con `404` o `AttributeError`.

- [ ] **Step 3: Implementar los endpoints en auth.py**

En `backend/app/routers/auth.py`, agregar los imports necesarios al inicio:

```python
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_pending_2fa_token,
    create_refresh_token,
    create_totp_setup_token,
    decode_token,
    generate_totp_secret,
    get_totp_provisioning_uri,
    hash_password,
    verify_password,
    verify_totp,
)
from app.models.invite_token import InviteToken
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ConfirmRegisterRequest,
    LoginRequest,
    PendingTokenResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    RegenerateTOTPRequest,
    RegenerateTOTPResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyTOTPRequest,
)
from app.services import session_store
from app.services.auth import authenticate_user
from datetime import timedelta
```

Luego agregar los dos endpoints nuevos al final del router (antes del cierre):

```python
@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    invite = db.query(InviteToken).filter(
        InviteToken.token == body.token,
        InviteToken.tipo == "invite",
        InviteToken.usado_en.is_(None),
    ).first()
    if not invite:
        raise HTTPException(status_code=400, detail="Link de registro inválido o expirado")
    if invite.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link de registro inválido o expirado")

    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Nombre de usuario no disponible")

    totp_secret = generate_totp_secret()
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        totp_secret=totp_secret,
        is_active=False,
    )
    db.add(user)
    db.flush()

    totp_uri = get_totp_provisioning_uri(totp_secret, body.username, settings.TOTP_ISSUER)
    setup_token = create_totp_setup_token(str(user.id), str(invite.id))
    db.commit()

    return RegisterResponse(totp_uri=totp_uri, setup_token=setup_token)


@router.post("/register/confirm", status_code=204)
def confirm_register(body: ConfirmRegisterRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.setup_token)
        if payload.get("type") != "totp_setup":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token de setup inválido o expirado")

    user = db.query(User).filter(
        User.id == UUID(payload["sub"]),
        User.is_active.is_(False),
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado o ya confirmado")

    if not verify_totp(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Código del Authenticator incorrecto")

    invite = db.get(InviteToken, UUID(payload["invite_token_id"]))
    if invite:
        invite.usado_en = datetime.now(timezone.utc)

    user.is_active = True
    db.commit()
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
venv\Scripts\python -m pytest tests/test_register.py -v
```

Resultado esperado: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_register.py backend/app/routers/auth.py
git commit -m "feat(backend): POST /auth/register and /auth/register/confirm endpoints"
```

---

### Task 5: POST /auth/reset-password

**Files:**
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/tests/test_register.py` (agregar fixture reset_token y tests)

- [ ] **Step 1: Agregar fixture reset_token a conftest.py**

En `backend/tests/conftest.py`, agregar al final:

```python
@pytest.fixture
def reset_token(db, test_user):
    import secrets
    from datetime import datetime, timedelta, timezone
    from app.models.invite_token import InviteToken
    user, _ = test_user
    token = InviteToken(
        token=secrets.token_urlsafe(32),
        tipo="reset",
        user_id=user.id,
        expira_en=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(token)
    db.flush()
    return token
```

- [ ] **Step 2: Escribir tests failing**

Agregar al final de `backend/tests/test_register.py`:

```python
def test_reset_password_valid(client, reset_token, test_user):
    user, _ = test_user
    r = client.post("/auth/reset-password", json={
        "token": reset_token.token,
        "password": "NuevaPass456!",
    })
    assert r.status_code == 204

    # login con nueva contraseña
    r = client.post("/auth/login", json={"username": user.username, "password": "NuevaPass456!"})
    assert r.status_code == 200


def test_reset_password_invalid_token(client):
    r = client.post("/auth/reset-password", json={
        "token": "tokenquenoestaenladb",
        "password": "NuevaPass456!",
    })
    assert r.status_code == 400


def test_reset_password_token_already_used(client, reset_token, test_user):
    r = client.post("/auth/reset-password", json={
        "token": reset_token.token,
        "password": "NuevaPass456!",
    })
    assert r.status_code == 204
    # segundo intento con el mismo token
    r = client.post("/auth/reset-password", json={
        "token": reset_token.token,
        "password": "OtraPass789!",
    })
    assert r.status_code == 400
```

- [ ] **Step 3: Correr — deben fallar**

```bash
venv\Scripts\python -m pytest tests/test_register.py::test_reset_password_valid tests/test_register.py::test_reset_password_invalid_token tests/test_register.py::test_reset_password_token_already_used -v
```

Resultado esperado: FAIL con 404 o 405.

- [ ] **Step 4: Implementar el endpoint en auth.py**

Agregar después de `/register/confirm`:

```python
@router.post("/reset-password", status_code=204)
@limiter.limit("3/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_row = db.query(InviteToken).filter(
        InviteToken.token == body.token,
        InviteToken.tipo == "reset",
        InviteToken.usado_en.is_(None),
    ).first()
    if not token_row:
        raise HTTPException(status_code=400, detail="Link de reset inválido o expirado")
    if token_row.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link de reset inválido o expirado")

    user = db.query(User).filter(
        User.id == token_row.user_id,
        User.is_active.is_(True),
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    user.hashed_password = hash_password(body.password)
    token_row.usado_en = datetime.now(timezone.utc)
    db.commit()
```

- [ ] **Step 5: Correr — deben pasar**

```bash
venv\Scripts\python -m pytest tests/test_register.py -v
```

Resultado esperado: 11 PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_register.py backend/app/routers/auth.py
git commit -m "feat(backend): POST /auth/reset-password endpoint"
```

---

### Task 6: POST /auth/change-password + POST /auth/regenerate-totp

**Files:**
- Modify: `backend/app/routers/auth.py`
- Create: `backend/tests/test_change_credentials.py`

- [ ] **Step 1: Escribir tests failing**

```python
# backend/tests/test_change_credentials.py
import pyotp


def test_change_password_valid(client, auth_headers, test_user):
    user, totp_secret = test_user
    r = client.post("/auth/change-password", json={
        "old_password": "SecurePass123!",
        "new_password": "NuevaPass456!",
    }, headers=auth_headers)
    assert r.status_code == 204

    # login con nueva contraseña
    r = client.post("/auth/login", json={"username": user.username, "password": "NuevaPass456!"})
    assert r.status_code == 200


def test_change_password_wrong_old(client, auth_headers):
    r = client.post("/auth/change-password", json={
        "old_password": "contraseñaerronea",
        "new_password": "NuevaPass456!",
    }, headers=auth_headers)
    assert r.status_code == 401


def test_change_password_requires_auth(client):
    r = client.post("/auth/change-password", json={
        "old_password": "x",
        "new_password": "y",
    })
    assert r.status_code == 403


def test_regenerate_totp_valid(client, auth_headers, test_user):
    user, totp_secret = test_user
    code = pyotp.TOTP(totp_secret).now()
    r = client.post("/auth/regenerate-totp", json={"totp_code": code}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "totp_uri" in data
    assert data["totp_uri"].startswith("otpauth://totp/")
    # el nuevo URI debe tener un secret diferente al original
    new_secret = data["totp_uri"].split("secret=")[1].split("&")[0]
    assert new_secret != totp_secret


def test_regenerate_totp_wrong_code(client, auth_headers):
    r = client.post("/auth/regenerate-totp", json={"totp_code": "000000"}, headers=auth_headers)
    assert r.status_code == 401


def test_regenerate_totp_requires_auth(client):
    r = client.post("/auth/regenerate-totp", json={"totp_code": "123456"})
    assert r.status_code == 403
```

- [ ] **Step 2: Correr — deben fallar**

```bash
venv\Scripts\python -m pytest tests/test_change_credentials.py -v
```

Resultado esperado: 6 FAIL con 404 o 405.

- [ ] **Step 3: Implementar ambos endpoints en auth.py**

Agregar al final del router:

```python
@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()


@router.post("/regenerate-totp", response_model=RegenerateTOTPResponse)
def regenerate_totp(
    body: RegenerateTOTPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_totp(current_user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Código del Authenticator incorrecto")
    new_secret = generate_totp_secret()
    current_user.totp_secret = new_secret
    db.add(current_user)
    db.commit()
    totp_uri = get_totp_provisioning_uri(new_secret, current_user.username, settings.TOTP_ISSUER)
    return RegenerateTOTPResponse(totp_uri=totp_uri)
```

- [ ] **Step 4: Correr — deben pasar**

```bash
venv\Scripts\python -m pytest tests/test_change_credentials.py -v
```

Resultado esperado: 6 PASSED.

- [ ] **Step 5: Correr toda la suite**

```bash
venv\Scripts\python -m pytest tests/ -v
```

Resultado esperado: todos los tests anteriores siguen pasando.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_change_credentials.py backend/app/routers/auth.py
git commit -m "feat(backend): POST /auth/change-password and /auth/regenerate-totp endpoints"
```

---

### Task 7: Rate limiting en verify-totp y refresh

**Files:**
- Modify: `backend/app/routers/auth.py`

- [ ] **Step 1: Agregar @limiter.limit a verify-totp**

En `backend/app/routers/auth.py`, el endpoint `verify_totp_endpoint` debe cambiar de:

```python
@router.post("/verify-totp", response_model=TokenResponse)
def verify_totp_endpoint(body: VerifyTOTPRequest, db: Session = Depends(get_db)):
```

a:

```python
@router.post("/verify-totp", response_model=TokenResponse)
@limiter.limit("5/minute")
def verify_totp_endpoint(request: Request, body: VerifyTOTPRequest, db: Session = Depends(get_db)):
```

- [ ] **Step 2: Agregar @limiter.limit a refresh**

El endpoint `refresh` debe cambiar de:

```python
@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
```

a:

```python
@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
```

- [ ] **Step 3: Correr toda la suite (rate limiting desactivado en tests via RATELIMIT_ENABLED=false)**

```bash
venv\Scripts\python -m pytest tests/ -v
```

Resultado esperado: mismo número de tests pasando que antes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "security: rate limit /auth/verify-totp (5/min) and /auth/refresh (10/min)"
```

---

### Task 8: Frontend — instalar qrcode.react + actualizar auth service

**Files:**
- Modify: `frontend/src/services/auth.ts`

- [ ] **Step 1: Instalar qrcode.react**

```bash
cd frontend
npm install qrcode.react
```

Verificar que el paquete se agregó a `package.json`.

- [ ] **Step 2: Actualizar auth.ts con las 5 funciones nuevas**

El archivo completo debe quedar:

```typescript
// frontend/src/services/auth.ts
import { api } from './api'
import type { LoginResponse, TokenResponse } from '../types/domain'

let pendingToken: string | null = null

export function setPendingToken(token: string): void {
  pendingToken = token
}

export function getPendingToken(): string | null {
  return pendingToken
}

export function clearPendingToken(): void {
  pendingToken = null
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/login', { username, password })
  return res.data
}

export async function verifyTotp(pending_token: string, code: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/verify-totp', { pending_token, code })
  return res.data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function register(
  token: string,
  username: string,
  password: string
): Promise<{ totp_uri: string; setup_token: string }> {
  const res = await api.post('/auth/register', { token, username, password })
  return res.data
}

export async function confirmRegister(
  setup_token: string,
  totp_code: string
): Promise<void> {
  await api.post('/auth/register/confirm', { setup_token, totp_code })
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await api.post('/auth/reset-password', { token, password })
}

export async function changePassword(
  old_password: string,
  new_password: string
): Promise<void> {
  await api.post('/auth/change-password', { old_password, new_password })
}

export async function regenerateTotp(
  totp_code: string
): Promise<{ totp_uri: string }> {
  const res = await api.post('/auth/regenerate-totp', { totp_code })
  return res.data
}
```

- [ ] **Step 3: Verificar TypeScript**

```bash
cd frontend
npx tsc --noEmit
```

Resultado esperado: 0 errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/services/auth.ts
git commit -m "feat(frontend): install qrcode.react, add register/reset/change-password/regenerate-totp to auth service"
```

---

### Task 9: Frontend — RegisterPage

**Files:**
- Create: `frontend/src/pages/RegisterPage.tsx`

La página tiene dos pasos:
- Paso 1: formulario username + password + confirm password → POST /auth/register → si ok, ir a paso 2
- Paso 2: QR code display (qrcode.react) + input TOTP → POST /auth/register/confirm → redirect /login

- [ ] **Step 1: Crear RegisterPage.tsx**

```tsx
// frontend/src/pages/RegisterPage.tsx
import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { register, confirmRegister } from '../services/auth'

type Step = 'form' | 'qr'

export default function RegisterPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [step, setStep] = useState<Step>('form')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [totpUri, setTotpUri] = useState('')
  const [setupToken, setSetupToken] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    setLoading(true)
    try {
      const data = await register(token, username, password)
      setTotpUri(data.totp_uri)
      setSetupToken(data.setup_token)
      setStep('qr')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409) {
        setError('Ese nombre de usuario ya está en uso')
      } else if (err?.response?.status === 400) {
        setError('El link de registro es inválido o expiró')
      } else {
        setError(detail ?? 'Error al registrarse')
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await confirmRegister(setupToken, totpCode)
      navigate('/login', { state: { registered: true } })
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Código incorrecto. Verificá que escaneaste el QR y que la hora de tu dispositivo es correcta.')
      } else {
        setError('Error al confirmar. Intentá de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="max-w-sm w-full text-center space-y-2">
          <p className="text-slate-700 font-medium">Link inválido</p>
          <p className="text-sm text-slate-500">
            Necesitás un link de invitación válido para registrarte.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="max-w-sm w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-6">
        <div>
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <h1 className="text-xl font-semibold text-slate-900 mt-3">
            {step === 'form' ? 'Crear cuenta' : 'Configurar Authenticator'}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {step === 'form'
              ? 'Elegí tu usuario y contraseña.'
              : 'Escaneá el código QR con Google Authenticator o Authy, luego ingresá el código de 6 dígitos.'}
          </p>
        </div>

        {step === 'form' && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Usuario</label>
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="tu_usuario"
                required
                autoComplete="username"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Contraseña</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="mínimo 8 caracteres"
                required
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Confirmar contraseña</label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="repetí la contraseña"
                required
                autoComplete="new-password"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creando cuenta...' : 'Continuar'}
            </Button>
          </form>
        )}

        {step === 'qr' && (
          <form onSubmit={handleConfirm} className="space-y-5">
            <div className="flex justify-center">
              <div className="p-3 bg-white border border-slate-200 rounded-lg">
                <QRCodeSVG value={totpUri} size={180} />
              </div>
            </div>
            <p className="text-xs text-slate-500 text-center">
              Si no podés escanear el QR, copiá este código en tu app:
              <br />
              <span className="font-mono text-slate-700 break-all">
                {totpUri.split('secret=')[1]?.split('&')[0] ?? ''}
              </span>
            </p>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                Código del Authenticator (6 dígitos)
              </label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="123456"
                required
                autoComplete="one-time-code"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading || totpCode.length !== 6}>
              {loading ? 'Verificando...' : 'Confirmar y activar cuenta'}
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
cd frontend
npx tsc --noEmit
```

Resultado esperado: 0 errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/RegisterPage.tsx
git commit -m "feat(frontend): RegisterPage — two-step registration with QR confirmation"
```

---

### Task 10: Frontend — ResetPasswordPage

**Files:**
- Create: `frontend/src/pages/ResetPasswordPage.tsx`

- [ ] **Step 1: Crear ResetPasswordPage.tsx**

```tsx
// frontend/src/pages/ResetPasswordPage.tsx
import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { resetPassword } from '../services/auth'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    setLoading(true)
    try {
      await resetPassword(token, password)
      navigate('/login', { state: { passwordReset: true } })
    } catch (err: any) {
      if (err?.response?.status === 400) {
        setError('El link de reset es inválido o expiró. Pedile al administrador un nuevo link.')
      } else {
        setError('Error al cambiar la contraseña. Intentá de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="max-w-sm w-full text-center space-y-2">
          <p className="text-slate-700 font-medium">Link inválido</p>
          <p className="text-sm text-slate-500">
            Necesitás un link de reset válido. Pedíselo al administrador.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="max-w-sm w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-6">
        <div>
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <h1 className="text-xl font-semibold text-slate-900 mt-3">Nueva contraseña</h1>
          <p className="text-sm text-slate-500 mt-1">
            Tu Authenticator no cambia — solo actualizás tu contraseña.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Nueva contraseña</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="mínimo 8 caracteres"
              required
              autoComplete="new-password"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Confirmar contraseña</label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="repetí la contraseña"
              required
              autoComplete="new-password"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Guardando...' : 'Guardar contraseña'}
          </Button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verificar TypeScript**

```bash
npx tsc --noEmit
```

Resultado esperado: 0 errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ResetPasswordPage.tsx
git commit -m "feat(frontend): ResetPasswordPage — reset password via admin link"
```

---

### Task 11: Frontend — ChangePasswordModal + RegenerateTOTPModal + Sidebar + App.tsx

**Files:**
- Create: `frontend/src/components/profile/ChangePasswordModal.tsx`
- Create: `frontend/src/components/profile/RegenerateTOTPModal.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Crear ChangePasswordModal.tsx**

```tsx
// frontend/src/components/profile/ChangePasswordModal.tsx
import { useState } from 'react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { changePassword } from '../../services/auth'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ChangePasswordModal({ open, onClose }: Props) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  function reset() {
    setOldPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
    setSuccess(false)
  }

  function handleClose() {
    reset()
    onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas nuevas no coinciden')
      return
    }
    if (newPassword.length < 8) {
      setError('La nueva contraseña debe tener al menos 8 caracteres')
      return
    }
    setLoading(true)
    try {
      await changePassword(oldPassword, newPassword)
      setSuccess(true)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('La contraseña actual es incorrecta')
      } else {
        setError('Error al cambiar la contraseña')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-sm space-y-4">
        <h2 className="text-base font-semibold text-slate-900">Cambiar contraseña</h2>

        {success ? (
          <div className="space-y-4">
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
              Contraseña actualizada correctamente.
            </p>
            <Button className="w-full" onClick={handleClose}>Cerrar</Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Contraseña actual</label>
              <Input
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Nueva contraseña</label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="mínimo 8 caracteres"
                required
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Confirmar nueva contraseña</label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <div className="flex gap-2 pt-1">
              <Button type="button" variant="outline" className="flex-1" onClick={handleClose} disabled={loading}>
                Cancelar
              </Button>
              <Button type="submit" className="flex-1" disabled={loading}>
                {loading ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Crear RegenerateTOTPModal.tsx**

```tsx
// frontend/src/components/profile/RegenerateTOTPModal.tsx
import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { regenerateTotp } from '../../services/auth'

interface Props {
  open: boolean
  onClose: () => void
}

type Step = 'confirm' | 'qr'

export default function RegenerateTOTPModal({ open, onClose }: Props) {
  const [step, setStep] = useState<Step>('confirm')
  const [totpCode, setTotpCode] = useState('')
  const [newTotpUri, setNewTotpUri] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function handleClose() {
    setStep('confirm')
    setTotpCode('')
    setNewTotpUri('')
    setError('')
    onClose()
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await regenerateTotp(totpCode)
      setNewTotpUri(data.totp_uri)
      setStep('qr')
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Código incorrecto')
      } else {
        setError('Error al regenerar. Intentá de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-sm space-y-4">
        <h2 className="text-base font-semibold text-slate-900">Regenerar Authenticator</h2>

        {step === 'confirm' && (
          <>
            <p className="text-sm text-slate-500">
              Ingresá el código actual de tu Authenticator para confirmar que tenés acceso antes de generar uno nuevo.
            </p>
            <form onSubmit={handleConfirm} className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Código actual (6 dígitos)</label>
                <Input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  required
                  autoComplete="one-time-code"
                />
              </div>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <div className="flex gap-2">
                <Button type="button" variant="outline" className="flex-1" onClick={handleClose} disabled={loading}>
                  Cancelar
                </Button>
                <Button type="submit" className="flex-1" disabled={loading || totpCode.length !== 6}>
                  {loading ? 'Verificando...' : 'Continuar'}
                </Button>
              </div>
            </form>
          </>
        )}

        {step === 'qr' && (
          <div className="space-y-4">
            <p className="text-sm text-slate-500">
              Escaneá el nuevo QR con tu app de Authenticator. El código anterior ya no funcionará.
            </p>
            <div className="flex justify-center">
              <div className="p-3 bg-white border border-slate-200 rounded-lg">
                <QRCodeSVG value={newTotpUri} size={160} />
              </div>
            </div>
            <p className="text-xs text-slate-500 text-center">
              Código manual:
              <br />
              <span className="font-mono text-slate-700 break-all">
                {newTotpUri.split('secret=')[1]?.split('&')[0] ?? ''}
              </span>
            </p>
            <Button className="w-full" onClick={handleClose}>
              Listo
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Actualizar Sidebar.tsx**

Agregar `useState` para los dos modales y los botones de perfil. La sección del usuario (al final del sidebar) debe quedar:

```tsx
// Agregar imports al inicio:
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Send, FileEdit, Settings2, Upload, LogOut, KeyRound, ShieldCheck } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { cn } from '../../lib/utils'
import { fetchMinutas } from '../../services/minutas'
import { useAuth } from '../../hooks/useAuth'
import ExcelUploadModal from '../upload/ExcelUploadModal'
import ChangePasswordModal from '../profile/ChangePasswordModal'
import RegenerateTOTPModal from '../profile/RegenerateTOTPModal'
import type { EstadoMinuta } from '../../types/domain'
```

En el componente `Sidebar`, agregar los dos estados:
```tsx
const [changePassOpen, setChangePassOpen] = useState(false)
const [regenTOTPOpen, setRegenTOTPOpen] = useState(false)
```

La sección de perfil al fondo del sidebar (reemplazar el bloque `<div className="p-3 border-t ...">` completo):

```tsx
<div className="p-3 border-t border-slate-100 space-y-2">
  <Button
    variant="outline"
    size="sm"
    className="w-full gap-2"
    onClick={() => setUploadOpen(true)}
  >
    <Upload className="h-3.5 w-3.5" />
    Subir Excel
  </Button>
  <div className="flex items-center justify-between px-1">
    <div className="flex items-center gap-2">
      <div className="h-7 w-7 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-semibold text-slate-600">
        MO
      </div>
      <span className="text-xs text-slate-600">Middle Office</span>
    </div>
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => setChangePassOpen(true)}
        title="Cambiar contraseña"
      >
        <KeyRound className="h-3.5 w-3.5 text-slate-400" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => setRegenTOTPOpen(true)}
        title="Regenerar Authenticator"
      >
        <ShieldCheck className="h-3.5 w-3.5 text-slate-400" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={handleLogout}
        title="Cerrar sesión"
      >
        <LogOut className="h-3.5 w-3.5 text-slate-400" />
      </Button>
    </div>
  </div>
</div>
```

Y al final del return, antes del `</>` de cierre, agregar los dos modales:

```tsx
<ChangePasswordModal open={changePassOpen} onClose={() => setChangePassOpen(false)} />
<RegenerateTOTPModal open={regenTOTPOpen} onClose={() => setRegenTOTPOpen(false)} />
```

- [ ] **Step 4: Actualizar App.tsx con las dos rutas públicas**

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import TwoFactorPage from './pages/TwoFactorPage'
import RegisterPage from './pages/RegisterPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import PlantillaPage from './pages/PlantillaPage'
import ConfigDJPage from './pages/ConfigDJPage'
import AppLayout from './components/layout/AppLayout'
import AuthGuard from './components/layout/AuthGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/2fa" element={<TwoFactorPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/borradores" element={<DashboardPage estado="BORRADOR" />} />
          <Route path="/dashboard/enviados" element={<DashboardPage estado="ENVIADO" />} />
          <Route path="/dashboard/plantilla" element={<PlantillaPage />} />
          <Route path="/dashboard/config-dj" element={<ConfigDJPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/dashboard/borradores" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
```

- [ ] **Step 5: Verificar TypeScript**

```bash
cd frontend
npx tsc --noEmit
```

Resultado esperado: 0 errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/profile/ frontend/src/components/layout/Sidebar.tsx frontend/src/App.tsx
git commit -m "feat(frontend): ChangePasswordModal, RegenerateTOTPModal, profile buttons in Sidebar, public routes /register and /reset-password"
```

---

### Task 12: Verificación final

- [ ] **Step 1: Correr toda la suite de backend**

```bash
cd backend
venv\Scripts\python -m pytest tests/ -v
```

Resultado esperado: todos los tests pasan. Los nuevos deben sumar al total anterior (era 88).

- [ ] **Step 2: Verificar que el backend arranca**

```bash
venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Resultado esperado: `Application startup complete.` sin errores.

- [ ] **Step 3: Build del frontend sin errores TypeScript**

```bash
cd frontend
npm run build
```

Resultado esperado: `✓ built in X.XXs` sin errores de TypeScript.

- [ ] **Step 4: Commit final del ADR y plan (si no están commiteados)**

```bash
git add docs/adr/0008-registro-invite-token-gestion-credenciales.md
git add docs/superpowers/plans/2026-06-15-registro-invite-token-gestion-credenciales.md
git commit -m "docs: ADR-0008 and implementation plan for invite-token registration and credential management"
```

---

## Self-Review

**Spec coverage:**
- ✅ Tabla invite_tokens (Task 1)
- ✅ Script admin create_invite.py (Task 2)
- ✅ POST /auth/register + /auth/register/confirm, dos pasos (Task 4)
- ✅ POST /auth/reset-password (Task 5)
- ✅ POST /auth/change-password + /auth/regenerate-totp (Task 6)
- ✅ Rate limiting verify-totp y refresh (Task 7)
- ✅ RegisterPage con QR (Task 9)
- ✅ ResetPasswordPage (Task 10)
- ✅ ChangePasswordModal + RegenerateTOTPModal en Sidebar (Task 11)
- ✅ App.tsx rutas públicas /register y /reset-password (Task 11)

**Placeholder scan:** Ningún TBD o "implement later" encontrado.

**Type consistency:**
- `RegisterResponse` definido en Task 3, usado en Task 4 (backend) y Task 9 (frontend usa `{ totp_uri, setup_token }` inline)
- `RegenerateTOTPResponse.totp_uri` consistente en Task 6 (backend) y Task 11 (frontend usa `data.totp_uri`)
- `ChangePasswordRequest`, `RegenerateTOTPRequest` definidos en Task 3, usados en Task 6
- `confirmRegister`, `resetPassword`, `changePassword`, `regenerateTotp` definidos en Task 8, usados en Tasks 9-11
