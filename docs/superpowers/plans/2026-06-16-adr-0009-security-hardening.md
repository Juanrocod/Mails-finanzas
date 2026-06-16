# ADR-0009 Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar las 5 correcciones de seguridad pendientes del ADR-0009: limiter compartido (bug crítico), rate limit en /register/confirm, validación de contraseñas en backend, DateTime(timezone=True) en invite_tokens, y reducir REFRESH_TOKEN_EXPIRE_HOURS de 24 a 8.

**Architecture:** Un módulo central `app/core/limiter.py` unifica la instancia de slowapi `Limiter` (bug crítico actual: dos instancias separadas = cero protección real en producción). Los `field_validator` de Pydantic refuerzan la política de contraseñas en la capa de API. Una migración Alembic corrige el schema: timezone en invite_tokens, elimina índice duplicado y borra tablas de Fase 2 que violan ADR-0006.

**Tech Stack:** FastAPI, slowapi, Pydantic v2 `field_validator`, SQLAlchemy 2.x, Alembic, PostgreSQL / SQLite (tests)

---

## File Map

| Archivo | Acción | Responsabilidad |
|---------|--------|----------------|
| `backend/app/core/limiter.py` | **NUEVO** | Instancia compartida de `Limiter`, desactivable vía `RATELIMIT_ENABLED=false` |
| `backend/app/main.py` | Modificar | Importar limiter desde `core/limiter.py`, eliminar instanciación local |
| `backend/app/routers/auth.py` | Modificar | Importar limiter compartido; agregar `@limiter.limit` en `/register/confirm`; eliminar `.replace(tzinfo=timezone.utc)` |
| `backend/app/schemas/auth.py` | Modificar | `field_validator` de contraseña en `RegisterRequest`, `ResetPasswordRequest`, `ChangePasswordRequest` |
| `backend/app/models/invite_token.py` | Modificar | `DateTime` → `DateTime(timezone=True)` en `expira_en`, `usado_en`, `creado_en` |
| `backend/app/core/config.py` | Modificar | `REFRESH_TOKEN_EXPIRE_HOURS: int = 8` |
| `backend/alembic/versions/0004_security_hardening.py` | **NUEVO** | Timezone fix, drop índice duplicado, drop tablas Fase 2 y sus enum types |

---

### Task 1: Limiter compartido — crear core/limiter.py y actualizar main.py + auth.py

**El bug:** `auth.py` (línea 47) crea `limiter = Limiter(key_func=get_remote_address)` independiente del `limiter` registrado en `app.state.limiter` de `main.py`. slowapi usa la instancia para almacenar contadores — dos instancias = dos stores separados. Resultado: ningún `@limiter.limit()` en `auth.py` tenía efecto real en producción.

**Files:**
- Create: `backend/app/core/limiter.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/auth.py` (solo sección de imports + línea 47)

- [ ] **Step 1: Crear `backend/app/core/limiter.py`**

```python
# backend/app/core/limiter.py
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("RATELIMIT_ENABLED", "true").lower() != "false",
)
```

El parámetro `enabled` de `Limiter` es la API oficial de slowapi para desactivarlo. Lo leemos desde la misma variable de entorno que ya setea el `conftest.py`, así que los tests siguen funcionando sin cambios en el conftest.

- [ ] **Step 2: Reemplazar `backend/app/main.py` completo**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter
from app.routers import auth, uploads
from app.routers import session as session_router

app = FastAPI(title="Gestión de Órdenes Bursátiles — MVP", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(session_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Actualizar imports de `backend/app/routers/auth.py`**

Reemplazar el bloque de imports (líneas 1–47 del archivo actual) con:

```python
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
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

router = APIRouter(prefix="/auth", tags=["auth"])
```

Se eliminan `from slowapi import Limiter`, `from slowapi.util import get_remote_address`, y la línea `limiter = Limiter(key_func=get_remote_address)`. Se agrega `from app.core.limiter import limiter`.

- [ ] **Step 4: Ejecutar tests para verificar que nada se rompe**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Resultado esperado: todos los tests pasan. Si alguno falla con `AttributeError` sobre `limiter`, verificar que el import en `auth.py` sea `from app.core.limiter import limiter` (sin instanciación local).

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/limiter.py backend/app/main.py backend/app/routers/auth.py
git commit -m "fix(security): limiter compartido via core/limiter.py — rate limiting funcional en producción"
```

---

### Task 2: Rate limiting en /register/confirm

**El problema:** `POST /auth/register/confirm` verifica el código TOTP de 6 dígitos (10⁶ combinaciones) durante los 10 minutos de vida del `setup_token` sin ningún rate limit. El fix es consistente con el límite ya existente en `/auth/verify-totp`.

**Files:**
- Modify: `backend/app/routers/auth.py` (función `confirm_register`)

- [ ] **Step 1: Verificar que los tests de registro pasan antes del cambio**

```bash
cd backend
python -m pytest tests/test_register.py -v --tb=short
```

Resultado esperado: todos los tests de `test_register.py` pasan.

- [ ] **Step 2: Agregar decorator y parámetro `request` a `confirm_register`**

Reemplazar la definición del endpoint:

```python
# ANTES:
@router.post("/register/confirm", status_code=204)
def confirm_register(body: ConfirmRegisterRequest, db: Session = Depends(get_db)):

# DESPUÉS:
@router.post("/register/confirm", status_code=204)
@limiter.limit("5/minute")
def confirm_register(request: Request, body: ConfirmRegisterRequest, db: Session = Depends(get_db)):
```

`request: Request` es obligatorio para slowapi — sin él el decorator no puede leer la IP del cliente y falla en runtime.

- [ ] **Step 3: Ejecutar tests de registro**

```bash
cd backend
python -m pytest tests/test_register.py -v --tb=short
```

Resultado esperado: todos los tests pasan. El rate limiting está desactivado en tests (`RATELIMIT_ENABLED=false` → `enabled=False` en `core/limiter.py`), así que el decorator no interfiere.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "feat(security): rate limit 5/min en /register/confirm — protección contra brute-force TOTP en setup"
```

---

### Task 3: Validación de contraseñas en backend (Pydantic field_validator)

**El problema:** `RegisterRequest`, `ResetPasswordRequest` y `ChangePasswordRequest` aceptan cualquier string como contraseña. Un atacante que llame a la API directamente (sin frontend) puede crear cuentas con `password="a"`. El fix agrega defensa en profundidad con las mismas reglas que el frontend.

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/tests/test_security.py` (agregar tests de validación de contraseñas)

- [ ] **Step 1: Agregar tests de validación al final de `backend/tests/test_security.py`**

Leer el archivo primero para no destruir el contenido existente. Luego agregar al final:

```python
# --- Tests de validación de contraseñas en backend (ADR-0009, sección 3) ---

import pytest as _pytest


class TestPasswordBackendValidation:

    def test_register_rejects_short_password(self):
        from app.schemas.auth import RegisterRequest
        with _pytest.raises(Exception):
            RegisterRequest(token="tok", username="u", password="Abc1!")

    def test_register_rejects_no_uppercase(self):
        from app.schemas.auth import RegisterRequest
        with _pytest.raises(Exception):
            RegisterRequest(token="tok", username="u", password="abc123!!")

    def test_register_rejects_no_number(self):
        from app.schemas.auth import RegisterRequest
        with _pytest.raises(Exception):
            RegisterRequest(token="tok", username="u", password="Abcdefg!")

    def test_register_rejects_no_special_char(self):
        from app.schemas.auth import RegisterRequest
        with _pytest.raises(Exception):
            RegisterRequest(token="tok", username="u", password="Abcdef12")

    def test_register_rejects_too_long_password(self):
        from app.schemas.auth import RegisterRequest
        with _pytest.raises(Exception):
            RegisterRequest(token="tok", username="u", password="A1!" + "a" * 70)

    def test_register_accepts_valid_password(self):
        from app.schemas.auth import RegisterRequest
        req = RegisterRequest(token="tok", username="u", password="SecurePass123!")
        assert req.password == "SecurePass123!"

    def test_reset_password_rejects_weak(self):
        from app.schemas.auth import ResetPasswordRequest
        with _pytest.raises(Exception):
            ResetPasswordRequest(token="tok", password="weak")

    def test_change_password_rejects_weak_new_password(self):
        from app.schemas.auth import ChangePasswordRequest
        with _pytest.raises(Exception):
            ChangePasswordRequest(old_password="cualquiera", new_password="weak")

    def test_login_accepts_any_password(self):
        """LoginRequest NO valida contraseña — debe aceptar cualquier string para comparar contra el hash."""
        from app.schemas.auth import LoginRequest
        req = LoginRequest(username="u", password="weak")
        assert req.password == "weak"

    def test_api_register_returns_422_on_weak_password(self, client):
        r = client.post(
            "/auth/register",
            json={"token": "some-token", "username": "user", "password": "weak"},
        )
        assert r.status_code == 422

    def test_api_reset_password_returns_422_on_weak_password(self, client):
        r = client.post(
            "/auth/reset-password",
            json={"token": "some-token", "password": "weak"},
        )
        assert r.status_code == 422
```

- [ ] **Step 2: Ejecutar los tests nuevos para verificar que FALLAN (schemas sin validación aún)**

```bash
cd backend
python -m pytest tests/test_security.py::TestPasswordBackendValidation -v --tb=short
```

Resultado esperado: la mayoría FALLA porque los schemas aún no tienen `field_validator`.

- [ ] **Step 3: Reemplazar `backend/app/schemas/auth.py` completo**

```python
import re
from pydantic import BaseModel, field_validator


def _validate_password(v: str) -> str:
    if not (8 <= len(v) <= 72):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[A-Z]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[0-9]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[^a-zA-Z0-9]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    return v


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


class RegisterRequest(BaseModel):
    token: str
    username: str
    password: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class RegisterResponse(BaseModel):
    totp_uri: str
    setup_token: str


class ConfirmRegisterRequest(BaseModel):
    setup_token: str
    totp_code: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class RegenerateTOTPRequest(BaseModel):
    totp_code: str


class RegenerateTOTPResponse(BaseModel):
    totp_uri: str
```

Notas clave:
- `_validate_password` es función de módulo (no método de clase) — evita repetición y es testeable de forma aislada.
- El mensaje de error es genérico en todos los casos — no revela qué regla específica falló (previene enumeración de política).
- `72` es el límite efectivo de bcrypt — valores más largos se truncan silenciosamente.
- `LoginRequest` **no** valida contraseña — login debe comparar contra el hash y aceptar lo que el usuario ingrese.

- [ ] **Step 4: Ejecutar tests de validación para verificar que PASAN**

```bash
cd backend
python -m pytest tests/test_security.py::TestPasswordBackendValidation -v --tb=short
```

Resultado esperado: todos los tests PASAN.

- [ ] **Step 5: Ejecutar suite completa para verificar que tests existentes siguen pasando**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Resultado esperado: todos pasan. Los tests existentes en `test_change_credentials.py` y `test_register.py` ya usan `"SecurePass123!"` que cumple las reglas nuevas. Si algún test usa una contraseña débil como fixture, actualizarlo a `"SecurePass123!"`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/tests/test_security.py
git commit -m "feat(security): validación de contraseñas en backend — field_validator Pydantic, defensa en profundidad"
```

---

### Task 4: DateTime(timezone=True) en modelo invite_token + fix comparaciones

**El problema:** `invite_tokens.expira_en` (y `usado_en`, `creado_en`) están declaradas como `DateTime()` sin timezone. En PostgreSQL esto es `TIMESTAMP WITHOUT TIME ZONE`. El código compara con `datetime.now(timezone.utc)` usando `.replace(tzinfo=timezone.utc)` como workaround frágil — si el servidor de DB no corre en UTC, las comparaciones son incorrectas.

**Files:**
- Modify: `backend/app/models/invite_token.py`
- Modify: `backend/app/routers/auth.py` (dos comparaciones de expiración)

- [ ] **Step 1: Reemplazar `backend/app/models/invite_token.py` completo**

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
    expira_en = Column(DateTime(timezone=True), nullable=False)
    usado_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 2: Remover el workaround `.replace(tzinfo=timezone.utc)` en auth.py**

Con `DateTime(timezone=True)`, SQLAlchemy retorna datetimes timezone-aware tanto en PostgreSQL como en SQLite 2.x. La comparación directa es correcta.

**En la función `register`** — cambiar la comparación de expiración:

```python
# ANTES:
if invite.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):

# DESPUÉS:
if invite.expira_en < datetime.now(timezone.utc):
```

**En la función `reset_password`** — cambiar la comparación de expiración:

```python
# ANTES:
if token_row.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):

# DESPUÉS:
if token_row.expira_en < datetime.now(timezone.utc):
```

- [ ] **Step 3: Ejecutar todos los tests**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Resultado esperado: todos pasan.

**Si algún test falla con `TypeError: can't compare offset-naive and offset-aware datetimes`:** significa que la versión de SQLAlchemy retorna datetimes naive en SQLite. En ese caso, revertir solo el cambio en `auth.py` (volver a `.replace(tzinfo=timezone.utc)`) — el cambio en el modelo sigue siendo correcto para PostgreSQL.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/invite_token.py backend/app/routers/auth.py
git commit -m "fix(security): DateTime(timezone=True) en invite_tokens — timezone correcto en PostgreSQL"
```

---

### Task 5: REFRESH_TOKEN_EXPIRE_HOURS = 8

Mitigación para la ausencia de revocación de refresh tokens server-side (pospuesta a Fase 2, ADR-0009 sección 7). Reducir TTL de 24h a 8h alinea el refresh token con el access token y reduce la ventana de exposición ante un token robado.

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Reemplazar `backend/app/core/config.py` completo**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    TOTP_ISSUER: str = "GestionMails"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_HOURS: int = 8
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

- [ ] **Step 2: Ejecutar tests**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Resultado esperado: todos los tests pasan. El TTL del token no afecta los tests existentes.

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "fix(security): REFRESH_TOKEN_EXPIRE_HOURS 24→8h — ventana reducida ante token robado sin revocación"
```

---

### Task 6: Migración 0004 — timezone, índice duplicado, drop tablas Fase 2

Esta migración alinea el schema de producción con (a) el cambio de modelo de Task 4, (b) ADR-0006 (sin persistencia de órdenes en master).

**Files:**
- Create: `backend/alembic/versions/0004_security_hardening.py`

> ⚠️ Esta migración elimina tablas (`ordenes`, `excel_uploads`, `audit_events`, `dj_templates`) y sus tipos enum. El `upgrade()` destruye datos si los hubiera — en la rama `master` nunca hubo datos de Fase 2, así que es seguro.

- [ ] **Step 1: Crear `backend/alembic/versions/0004_security_hardening.py`**

```python
"""security hardening post-audit

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Fix invite_tokens: DateTime → DateTime(timezone=True)
    # postgresql_using convierte los valores existentes de naive a UTC-aware en PostgreSQL.
    for col, nullable in [('expira_en', False), ('usado_en', True), ('creado_en', False)]:
        op.alter_column(
            'invite_tokens', col,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )

    # 2. Drop índice duplicado en invite_tokens.token
    # La migración 0003 creó tanto UniqueConstraint('token') (→ invite_tokens_token_key)
    # como op.create_index('ix_invite_tokens_token', ..., unique=True) — dos índices físicos.
    op.drop_index('ix_invite_tokens_token', table_name='invite_tokens')

    # 3. Drop tablas Fase 2 (violan ADR-0006: master no tiene persistencia de órdenes)
    # Orden respeta foreign keys: audit_events → ordenes → excel_uploads
    op.drop_index('ix_audit_events_orden_id', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_table('ordenes')
    op.drop_table('excel_uploads')
    op.drop_table('dj_templates')

    # 4. Drop enum types creados junto con las tablas Fase 2
    op.execute('DROP TYPE IF EXISTS accionaudit')
    op.execute('DROP TYPE IF EXISTS estadominuta')
    op.execute('DROP TYPE IF EXISTS condicionliquidacion')
    op.execute('DROP TYPE IF EXISTS tipoperacion')


def downgrade() -> None:
    # Recrear enum types primero (requeridos por las columnas de las tablas)
    op.execute("CREATE TYPE tipoperacion AS ENUM ('COMPRA', 'VENTA')")
    op.execute("CREATE TYPE condicionliquidacion AS ENUM ('CI', '24HS', '48HS')")
    op.execute(
        "CREATE TYPE estadominuta AS ENUM "
        "('BORRADOR', 'APROBADO', 'ENVIADO', 'CONFIRMADO', 'ALERTA')"
    )
    op.execute(
        "CREATE TYPE accionaudit AS ENUM "
        "('CREADA', 'EDITADA', 'APROBADA', 'ENVIADA', 'CONFIRMADA', 'ALERTA_GENERADA')"
    )

    # Recrear tablas Fase 2 vacías
    op.create_table(
        'dj_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('reglas', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('prioridad', sa.Integer(), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
    )
    op.create_table(
        'excel_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('usuario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nombre_archivo', sa.String(length=255), nullable=False),
        sa.Column('total_ordenes', sa.Integer(), nullable=False),
        sa.Column('ordenes_validas', sa.Integer(), nullable=False),
        sa.Column('ordenes_con_error', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'ordenes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('excel_upload_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cliente_nombre', sa.String(length=255), nullable=False),
        sa.Column('cliente_email', sa.String(length=512), nullable=False),
        sa.Column('cuenta_comitente', sa.String(length=256), nullable=False),
        sa.Column('cuenta_cotapartista', sa.String(length=256), nullable=False),
        sa.Column('instrumento', sa.String(length=100), nullable=False),
        sa.Column('tipo', sa.Enum('COMPRA', 'VENTA', name='tipoperacion'), nullable=False),
        sa.Column('cantidad', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('precio', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('moneda', sa.String(length=10), nullable=False),
        sa.Column('liquidacion', sa.Enum('CI', '24HS', '48HS', name='condicionliquidacion'), nullable=False),
        sa.Column('fecha_operacion', sa.DateTime(), nullable=False),
        sa.Column('dj_aplicada', sa.Boolean(), nullable=False),
        sa.Column('dj_tipo', sa.String(length=100), nullable=True),
        sa.Column('estado', sa.Enum('BORRADOR', 'APROBADO', 'ENVIADO', 'CONFIRMADO', 'ALERTA', name='estadominuta'), nullable=False),
        sa.Column('texto_minuta', sa.Text(), nullable=False),
        sa.Column('texto_editado', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['excel_upload_id'], ['excel_uploads.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('orden_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('usuario_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('accion', sa.Enum('CREADA', 'EDITADA', 'APROBADA', 'ENVIADA', 'CONFIRMADA', 'ALERTA_GENERADA', name='accionaudit'), nullable=False),
        sa.Column('ip_origen', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('detalle', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['orden_id'], ['ordenes.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_orden_id', 'audit_events', ['orden_id'], unique=False)

    # Restaurar índice duplicado en invite_tokens.token (para que downgrade sea simétrico)
    op.create_index('ix_invite_tokens_token', 'invite_tokens', ['token'], unique=True)

    # Revertir invite_tokens a DateTime sin timezone
    for col, nullable in [('expira_en', False), ('usado_en', True), ('creado_en', False)]:
        op.alter_column(
            'invite_tokens', col,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=nullable,
        )
```

- [ ] **Step 2: Verificar que el archivo es Python válido**

```bash
cd backend
python -m py_compile alembic/versions/0004_security_hardening.py && echo "OK"
```

Resultado esperado: `OK` sin errores.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0004_security_hardening.py
git commit -m "feat(db): migración 0004 — timezone invite_tokens, drop índice duplicado, drop tablas Fase 2"
```

---

### Task 7: Verificación final

- [ ] **Step 1: Ejecutar suite completa de tests**

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

Resultado esperado: todos los tests pasan. Confirmar que aparecen:
- `tests/test_auth.py` — PASSED
- `tests/test_register.py` — PASSED
- `tests/test_security.py` — PASSED (incluye `TestPasswordBackendValidation`)
- `tests/test_change_credentials.py` — PASSED
- `tests/test_session_router.py` — PASSED
- `tests/test_uploads.py` — PASSED

- [ ] **Step 2: Commit final si quedó algún archivo sin commitear**

```bash
git status
```

Si hay archivos modificados sin commit:

```bash
git add <archivos pendientes>
git commit -m "chore: ADR-0009 security hardening — verificación final"
```
