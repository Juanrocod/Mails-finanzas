# ADR-0006: Arquitectura MVP sin persistencia de órdenes

## Estado
Aceptado

## Contexto
El alcance original del proyecto (ADR-0001 a 0005) planificaba persistir todas las Órdenes, Minutas y AuditEvents en PostgreSQL. Antes de construir esa capa completa, se decide construir un MVP funcional que permita validar el flujo de trabajo de Middle Office con infraestructura mínima.

El objetivo del MVP es demostrar el ciclo completo: subir Excel → revisar minutas generadas → marcar como enviadas. No se requiere persistencia histórica en esta etapa; Middle Office reinicia el trabajo subiendo un nuevo Excel cada sesión.

## Decisiones

### 1. Base de datos: solo para autenticación

PostgreSQL se mantiene únicamente para la tabla de usuarios (auth). No se crean tablas para Órdenes, ExcelUpload, AuditEvents ni DJTemplates.

**Consecuencia:** los modelos SQLAlchemy `Order`, `ExcelUpload`, `AuditEvent` y `DJTemplate` no existen en el MVP. Las migraciones de Alembic solo cubren `users` y `sessions`.

### 2. Órdenes y Minutas en RAM

Las Minutas generadas a partir del Excel se almacenan en un diccionario en memoria (`dict[session_id, list[Minuta]]`) mientras dura la sesión autenticada. Al cerrar sesión o reiniciar el servidor, todo desaparece.

Esto es aceptable en el MVP porque:
- Las sesiones son cortas (una operativa por día).
- El Excel fuente puede volver a subirse si se necesita recuperar el trabajo.
- Evita diseñar un esquema de DB antes de que el dominio esté validado en uso real.

### 3. Endpoint de upload responde las minutas directamente

`POST /uploads/excel` parsea el Excel en memoria, genera las Minutas, las guarda en el store de sesión y **retorna la lista completa en la response**. No escribe nada a disco ni a DB.

### 4. Endpoints de sesión en lugar de endpoints de DB

Se reemplazan los endpoints que consultaban la DB por endpoints que leen el store en RAM:

| Endpoint | Descripción |
|----------|-------------|
| `POST /uploads/excel` | Procesa Excel → guarda en RAM → retorna minutas |
| `GET /session/minutas` | Lista minutas de la sesión actual |
| `PATCH /session/minutas/{id}/enviado` | Marca una minuta como ENVIADO en RAM |
| `GET /plantilla` | Retorna el texto de la plantilla estándar (RAM) |
| `PATCH /plantilla` | Actualiza la plantilla estándar en RAM |
| `GET /config/dj` | Retorna configuración de DJ (activo, texto de alerta) |
| `PATCH /config/dj` | Actualiza configuración de DJ en RAM |

### 5. Estados simplificados: solo BORRADOR y ENVIADO

La máquina de estados del ADR original (BORRADOR → APROBADO → ENVIADO → CONFIRMADO / ALERTA) se simplifica:

```
BORRADOR → ENVIADO
```

- Se elimina el estado APROBADO: el usuario revisa el texto y lo envía directamente.
- Se eliminan CONFIRMADO y ALERTA: no hay seguimiento post-envío en el MVP.
- El botón "Aprobar" del drawer se reemplaza por "Copiar contenido" (el usuario copia y pega en su cliente de mail).
- El botón "Enviado" marca la minuta y la mueve al tab Enviados.

### 6. Tabs del Dashboard simplificadas

| Tab anterior | Tab MVP |
|---|---|
| Borradores | Borradores ✓ |
| Aprobados | **Eliminado** |
| Enviados | Enviados ✓ |
| Confirmados | **Eliminado** |
| Alertas | **Eliminado** |
| Audit Trail | **Eliminado** |
| — | Plantilla Estándar ✓ (nueva) |
| — | Config DJ ✓ (nueva) |

### 7. Sin audit trail

No hay audit trail en el MVP. No hay qué auditar si nada persiste. La tab "Audit Trail" y el componente `AuditTrailSection` no se implementan.

### 8. Nueva tab: Plantilla Estándar

Editor de texto simple donde Middle Office puede modificar la plantilla base de mail. El texto editado se guarda en RAM y se usa en las minutas generadas de la sesión actual.

### 9. Nueva tab: Config DJ

Configuración de la Declaración Jurada con:
- Toggle activo/inactivo
- Textarea con el texto de alerta (mostrado con ícono triángulo ⚠ en la minuta)

### 10. Autenticación: sin cambios

Auth se mantiene igual que el diseño original: JWT, TOTP (2FA), bcrypt, refresh tokens. Es la única parte que toca la DB.

## Consecuencias

**Positivo:**
- Backend radicalmente más simple: sin modelos de órdenes, sin migraciones complejas.
- Permite validar el flujo de UX antes de comprometerse con un esquema de DB.
- Despliegue más liviano para la primera demo.

**Negativo:**
- Sin persistencia: si el servidor se reinicia, las minutas de la sesión se pierden.
- Sin historial: no se puede auditar qué se procesó en sesiones anteriores.
- Sin multi-tab: si el mismo usuario abre otra pestaña del browser, el estado puede desincronizarse (store en RAM por session_id).

**Neutro:**
- El código de la rama `con-db(f2)` preserva la arquitectura con persistencia completa para la Fase 2. El MVP en `master` es un camino paralelo, no un reemplazo definitivo.

## ADRs relacionados

- ADR-0001: entrada vía Excel — se mantiene igual
- ADR-0002: envío manual Fase 1 — se mantiene igual (el envío sigue siendo manual)
- ADR-0003: stack FastAPI + React — se mantiene igual
- ADR-0004: autenticación 2FA — se mantiene igual
- ADR-0005: UI architecture — se actualiza: eliminar tabs APROBADO/CONFIRMADO/ALERTA/AUDIT, agregar PLANTILLA y CONFIG DJ
