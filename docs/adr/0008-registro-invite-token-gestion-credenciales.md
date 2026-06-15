# ADR-0008: Registro por Invite Token y Gestión de Credenciales

## Estado
Aceptado

## Contexto

El sistema no tiene ningún mecanismo para crear usuarios ni para configurar el TOTP
desde la interfaz. El único usuario existente debe crearse directamente en la DB o
mediante un script manual. Tampoco hay forma de cambiar la contraseña, recuperarla
si se olvida, ni regenerar el secreto del Authenticator si el usuario pierde acceso
a su app de 2FA.

Adicionalmente, dos endpoints críticos del flujo de autenticación carecen de rate
limiting: `/auth/verify-totp` y `/auth/refresh`. Un atacante que robe la contraseña
puede hacer fuerza bruta al código TOTP (1.000.000 de combinaciones); uno que robe
el refresh token puede obtener access tokens indefinidamente.

## Decisiones

### 1. Registro solo por invite token — sin registro público

No existe una pantalla de registro pública. El operador (admin) genera un link de
un solo uso mediante un script en consola. Solo quien reciba ese link puede crear
su cuenta. Esto evita el riesgo de registros no autorizados en un sistema regulado.

El link tiene formato:
```
https://app.example.com/register?token=<token_urlsafe_32>
```

### 2. Nueva tabla `invite_tokens`

```sql
id         UUID PRIMARY KEY
token      VARCHAR(64) UNIQUE NOT NULL  -- secrets.token_urlsafe(32)
tipo       VARCHAR(10) NOT NULL         -- 'invite' | 'reset'
user_id    UUID REFERENCES users(id)    -- NULL para invite, FK para reset
expira_en  DATETIME NOT NULL            -- now() + 48hs
usado_en   DATETIME                     -- NULL = disponible, timestamp = usado
creado_en  DATETIME NOT NULL
```

Patrón: el token queda inutilizable en cuanto se usa O expira (lo que ocurra
primero). No hay reutilización.

### 3. Registro en dos pasos para garantizar que el Authenticator funcione

El registro no activa la cuenta inmediatamente. Requiere confirmar que el usuario
escaneó el QR correctamente:

```
POST /auth/register
  { token, username, password }
  → crea User(is_active=False) + genera TOTP secret
  → devuelve { totp_uri, setup_token }   ← setup_token: JWT 10 min, type="totp_setup"
  → NO marca el invite_token como usado todavía

Frontend muestra QR (qrcode.react)

POST /auth/register/confirm
  { setup_token, totp_code }
  → verifica TOTP code contra el secreto del usuario inactivo
  → activa User(is_active=True)
  → marca invite_token.usado_en = now()
  → 204 No Content
```

Si el usuario cierra la página antes de confirmar: la cuenta queda inactiva y el
invite token sigue disponible (se puede reintentar con el mismo link dentro de
las 48hs). Si el setup_token (10 min) expiró, hay que iniciar desde `/auth/register`
de nuevo.

### 4. Script de consola para el admin — sin endpoint de gestión en la API

El admin genera tokens desde la terminal:

```bash
# Generar link de registro (usuario nuevo)
python create_invite.py invite

# Generar link de reset de contraseña para usuario existente
python create_invite.py reset --username juan
```

No existe ningún endpoint HTTP para generar tokens. Esto reduce la superficie de
ataque — la generación de acceso requiere acceso al servidor.

### 5. Reset de contraseña por link de admin — sin SMTP

El sistema no envía emails. Cuando un usuario olvida su contraseña, el admin
genera un reset token y se lo envía por el canal que corresponda (Slack, WhatsApp,
etc.). El link lleva al usuario a una pantalla simple de nueva contraseña.

```
POST /auth/reset-password
  { token, password }
  → valida reset token (tipo='reset', user_id set, no usado, no expirado)
  → actualiza hashed_password
  → marca token como usado
  → 204 No Content
```

El TOTP secret **no cambia** con el reset de contraseña. El usuario sigue usando
el mismo Authenticator.

### 6. Cambio de contraseña desde dentro de la app

El usuario autenticado puede cambiar su contraseña ingresando la contraseña actual:

```
POST /auth/change-password  (requiere Bearer token)
  { old_password, new_password }
  → verifica old_password
  → actualiza hashed_password
  → 204 No Content
```

### 7. Regeneración del TOTP — independiente del password

Si el usuario pierde acceso a su app de Authenticator (cambio de celular, etc.),
puede regenerar el TOTP secret desde la app:

```
POST /auth/regenerate-totp  (requiere Bearer token)
  { totp_code }   ← código del Authenticator ACTUAL (para verificar que lo tiene)
  → verifica el código TOTP actual
  → genera nuevo totp_secret
  → devuelve { totp_uri } para el nuevo QR
```

El TOTP y la contraseña son factores independientes: cambiar uno no afecta al otro.

### 8. Rate limiting en verify-totp y refresh

| Endpoint | Límite actual | Límite nuevo |
|---|---|---|
| `POST /auth/login` | 5/min ✅ | sin cambios |
| `POST /auth/verify-totp` | sin límite ❌ | **5/min** |
| `POST /auth/refresh` | sin límite ❌ | **10/min** |
| `POST /auth/register` | — | **3/min** |
| `POST /auth/reset-password` | — | **3/min** |

En tests `RATELIMIT_ENABLED=false` (ya configurado en `conftest.py`), por lo que
estos límites no afectan el test suite.

### 9. Soporte multi-usuario sin cambio de esquema

La tabla `users` ya soporta N usuarios (UUID como PK, sin restricción de fila
única). Para agregar un segundo operador en el futuro: el admin genera otro invite
token y se lo envía. No hay cambio de esquema ni configuración adicional.

Las sesiones en RAM están aisladas por `user_id`, por lo que múltiples usuarios
activos simultáneamente no se interfieren.

### 10. Frontend: QR via qrcode.react

La URI `otpauth://...` generada por `pyotp` se renderiza como QR usando
`qrcode.react` (TypeScript types incluidos en el paquete desde v3). Se muestra
en `RegisterPage` (registro) y `RegenerateTOTPModal` (regeneración).

## Archivos nuevos / modificados

**Backend:**
- `backend/app/models/invite_token.py` (nuevo)
- `backend/alembic/versions/0003_add_invite_tokens.py` (nuevo)
- `backend/alembic/env.py` (modifica — importar InviteToken)
- `backend/app/schemas/auth.py` (modifica — 6 schemas nuevos)
- `backend/app/core/security.py` (modifica — add create_totp_setup_token)
- `backend/app/routers/auth.py` (modifica — 5 endpoints nuevos + 2 rate limits)
- `backend/create_invite.py` (nuevo — script de consola)
- `backend/tests/test_register.py` (nuevo)
- `backend/tests/test_change_credentials.py` (nuevo)
- `backend/tests/conftest.py` (modifica — fixtures invite_token, reset_token)

**Frontend:**
- `frontend/src/pages/RegisterPage.tsx` (nuevo)
- `frontend/src/pages/ResetPasswordPage.tsx` (nuevo)
- `frontend/src/components/profile/ChangePasswordModal.tsx` (nuevo)
- `frontend/src/components/profile/RegenerateTOTPModal.tsx` (nuevo)
- `frontend/src/services/auth.ts` (modifica — 5 funciones nuevas)
- `frontend/src/components/layout/Sidebar.tsx` (modifica — botones de perfil)
- `frontend/src/App.tsx` (modifica — rutas públicas /register y /reset-password)

## Consecuencias

**Positivo:**
- El usuario puede autogestionar contraseña y Authenticator sin intervención técnica.
- Registro controlado por invite: solo accede quien el admin autoriza.
- Sin SMTP ni dependencia externa para el reset.
- Rate limiting cierra el hueco de fuerza bruta en 2FA.
- Soporte multi-usuario sin deuda técnica.

**Negativo:**
- Si el admin no tiene acceso al servidor para correr el script, no puede generar
  invite/reset tokens (por diseño — es una restricción de seguridad, no un bug).
- El reset requiere canal de comunicación alternativo (Slack, etc.) entre admin y
  usuario. Aceptable para un sistema de un operador regulado.

**Neutro:**
- Las minutas en RAM (ADR-0006) no cambian.
- La máquina de estados BORRADOR → ENVIADO no cambia.
- La plantilla y config DJ en DB (ADR-0007) no cambian.

## ADRs relacionados

- ADR-0004: autenticación 2FA — se extiende con endpoints de gestión de credenciales.
- ADR-0006: sin persistencia de órdenes — no cambia.
- ADR-0007: plantilla y config DJ en DB — no cambia.
