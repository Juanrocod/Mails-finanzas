# ADR-0009: Hardening de Seguridad — Correcciones Post-Auditoría

## Estado
Aceptado

## Contexto

Tras implementar el ADR-0008 (registro por invite token y gestión de credenciales),
se realizó una auditoría de seguridad de cuatro agentes independientes que cubrió
backend, frontend, capa de DB/modelos y análisis transversal. La auditoría arrojó
45 findings. Este ADR documenta las decisiones de remediación y los trade-offs
aceptados explícitamente.

**Hallazgo crítico transversal descubierto:** el sistema tenía rate limiting
declarado en código pero completamente no funcional en producción: `auth.py` instanciaba
su propio `Limiter` independiente del registrado en `app.state.limiter`, por lo que
ningún decorador `@limiter.limit()` tenía efecto real fuera de los tests.

**Verificación previa al código:** `git log --all -- backend/.env` no devolvió
resultados — el `.env` nunca fue commiteado. Las claves actuales son seguras.

## Decisiones

### 1. Limiter compartido via módulo `app/core/limiter.py`

**Problema:** `auth.py` definía `limiter = Limiter(key_func=get_remote_address)` en
la línea 47, creando una instancia separada de la registrada en `app.state.limiter`.
slowapi requiere la misma instancia para que los contadores funcionen. Resultado:
cero protección real en todos los endpoints de autenticación.

**Decisión:** mover la instancia única de `Limiter` a `backend/app/core/limiter.py`
e importarla tanto en `main.py` como en `auth.py`. Un único objeto, un único storage
de contadores.

```python
# app/core/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

```python
# main.py
from app.core.limiter import limiter
app.state.limiter = limiter

# auth.py
from app.core.limiter import limiter
```

La variable de entorno `RATELIMIT_ENABLED=false` del conftest no es nativa de
slowapi — se reemplaza por el parámetro oficial `enabled=False` al instanciar el
`Limiter` en contexto de tests.

### 2. Rate limiting en `/register/confirm`

**Problema:** el endpoint `POST /auth/register/confirm` no tenía `@limiter.limit()`.
Un atacante con un `setup_token` válido (JWT de 10 minutos) podía hacer fuerza
bruta al código TOTP de 6 dígitos sin restricción del servidor.

**Decisión:** agregar `@limiter.limit("5/minute")` al endpoint, consistente con el
límite de `/auth/verify-totp`.

### 3. Validación de contraseñas en el backend (schemas Pydantic)

**Problema:** los schemas `RegisterRequest`, `ResetPasswordRequest` y
`ChangePasswordRequest` definían el campo `password`/`new_password` como `str`
puro, sin restricciones de longitud ni complejidad. Un atacante que llame
directamente a la API (sin pasar por el frontend) puede crear cuentas con
contraseñas de un carácter.

**Decisión:** agregar un `@field_validator` reutilizable en `schemas/auth.py` que
aplique las mismas reglas que el frontend:

- Mínimo 8 caracteres
- Al menos una mayúscula (`[A-Z]`)
- Al menos un número (`[0-9]`)
- Al menos un carácter especial (`[^a-zA-Z0-9]`)
- Máximo 72 caracteres (límite efectivo de bcrypt — valores más largos son
  truncados silenciosamente)

La validación vive ahora en ambas capas (defensa en profundidad). El mensaje de
error del backend es genérico para no revelar qué regla específica falló.

### 4. `DateTime(timezone=True)` en `invite_tokens`

**Problema:** la columna `expira_en` (y `usado_en`, `creado_en`) en `invite_tokens`
se declaró como `DateTime()` sin `timezone=True`. En PostgreSQL esto se mapea a
`TIMESTAMP WITHOUT TIME ZONE`. El código de validación usaba
`invite.expira_en.replace(tzinfo=timezone.utc)` como workaround, que es frágil si
el servidor de DB no corre en UTC.

**Decisión:** cambiar a `DateTime(timezone=True)` en el modelo y crear una
migración correctiva `0004` que:

1. Agrega `timezone=True` a los tres campos DateTime de `invite_tokens`.
2. Elimina el índice duplicado en `invite_tokens.token` (el modelo tenía tanto
   `UniqueConstraint('token')` como `op.create_index(..., unique=True)` sobre la
   misma columna — dos índices físicos distintos en PostgreSQL).
3. Elimina las tablas de Fase 2 (`ordenes`, `excel_uploads`, `audit_events`,
   `dj_templates`) que la migración inicial creó en la rama `master` por arrastre
   del autogenerate de Alembic. Ningún modelo ni router de `master` las usa, pero
   su existencia en el schema de producción viola ADR-0006 (sin persistencia de
   órdenes) al crear superficie de escritura accidental.

### 5. Reset de contraseña sin TOTP — decisión explícitamente aceptada

**Problema identificado en auditoría:** `POST /auth/reset-password` cambia la
contraseña verificando solo el token de reset (algo que tenés), sin verificar el
código TOTP (algo que sos). Esto crea un bypass parcial del 2FA para quien
intercepte el link de reset.

**Decisión:** mantener el diseño actual. Justificación:

- El canal de distribución del link (Slack, WhatsApp del broker) es el mismo nivel
  de confianza que el canal de distribución del invite token — está bajo control
  operativo del admin.
- El TOTP secret **no cambia** con el reset de contraseña: el usuario sigue
  teniendo su Authenticator. El atacante que solo tiene el link de reset puede
  cambiar la contraseña pero no puede completar el login sin el código TOTP.
- Para un sistema de pocos operadores internos con canal de comunicación controlado,
  el riesgo residual es aceptable.
- Agregar TOTP al reset introduce complejidad: si el usuario perdió acceso al
  Authenticator además de la contraseña, el reset con TOTP obligatorio lo bloquea
  permanentemente.

**Riesgo aceptado:** si el canal de distribución del link se ve comprometido, un
atacante puede cambiar la contraseña pero no puede autenticarse. El impacto queda
acotado a denegación de servicio (el usuario legítimo no puede entrar hasta que el
admin genere otro reset token).

### 6. Refresh token — sin revocación en el MVP

**Problema identificado en auditoría:** los refresh tokens (24hs de vida) no tienen
mecanismo de revocación server-side. Un logout solo limpia el session store en RAM,
no invalida el token. Un token robado permite obtener access tokens durante 24hs.

**Decisión:** posponer la revocación de refresh tokens a Fase 2 por las siguientes
razones:

- El sistema tiene un número muy acotado de usuarios (operadores internos del
  broker), lo que reduce la superficie de ataque real.
- Los tokens viven en variable de módulo JavaScript en el cliente (no en
  localStorage/cookies), lo que elimina el principal vector de robo (XSS sobre
  storage).
- La implementación correcta requiere una tabla `refresh_tokens` en DB con rotación
  atómica, lo que es un cambio de schema no trivial para el MVP.

**Mitigación en MVP:** reducir `REFRESH_TOKEN_EXPIRE_HOURS` de 24 a 8 horas
(alineado con `ACCESS_TOKEN_EXPIRE_HOURS`). Documentado en `.env.example`.

## Archivos nuevos / modificados

**Backend:**
- `backend/app/core/limiter.py` (nuevo — instancia compartida de Limiter)
- `backend/app/main.py` (modifica — importar limiter desde core/limiter.py)
- `backend/app/routers/auth.py` (modifica — importar limiter desde core/limiter.py,
  agregar @limiter.limit a /register/confirm)
- `backend/app/schemas/auth.py` (modifica — @field_validator de contraseña)
- `backend/app/models/invite_token.py` (modifica — DateTime(timezone=True))
- `backend/alembic/versions/0004_security_hardening.py` (nuevo — timezone,
  índice duplicado, drop tablas Fase 2)
- `backend/tests/conftest.py` (modifica — RATELIMIT_ENABLED reemplazado por
  parámetro nativo de slowapi)

## Consecuencias

**Positivo:**
- El rate limiting funciona de verdad en producción por primera vez.
- La política de contraseñas se aplica también cuando se llama a la API directamente.
- El schema de DB en `master` queda limpio: solo las tablas del MVP, sin superficie
  de persistencia accidental de órdenes.
- Los comparadores de fechas de invite tokens funcionan correctamente en PostgreSQL
  independientemente del timezone del servidor de DB.

**Negativo:**
- La refactorización del limiter requiere tocar `main.py` y `auth.py` en simultáneo;
  si se hace a medias el sistema queda sin protección.
- La migración 0004 elimina tablas en `downgrade` → `upgrade` sequence;
  el `downgrade` de 0004 recrea las tablas vacías (no tiene datos que restaurar).

**Neutro:**
- El comportamiento de negocio no cambia: los flujos de registro, login,
  reset y cambio de credenciales funcionan igual para el usuario final.
- Los tests existentes siguen pasando (el fix del limiter requiere ajustar el
  conftest pero no los tests de funcionalidad).

## Riesgos aceptados explícitamente

| Riesgo | Aceptado por | Mitigación |
|--------|-------------|------------|
| Reset sin TOTP | Diseño consciente | Canal de distribución controlado por admin; TOTP sigue siendo requerido para login |
| Refresh token sin revocación | Fase 2 | TTL reducido a 8hs; tokens en memoria (no storage) |
| Token de invite expuesto en URL | Fase 2 | TTL de 48hs; canal de distribución controlado |
| Session store sin TTL | Fase 2 | Un solo worker en MVP; minutas son efímeras por diseño |

## ADRs relacionados

- ADR-0004: autenticación 2FA — rate limiting ahora funcional extiende la protección.
- ADR-0006: sin persistencia de órdenes — migración 0004 limpia las tablas de Fase 2
  que contradecían este ADR en el schema de DB.
- ADR-0008: registro por invite token — este ADR corrige bugs de implementación del 0008,
  no cambia sus decisiones de diseño.
