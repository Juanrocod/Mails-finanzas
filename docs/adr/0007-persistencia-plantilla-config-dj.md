# ADR-0007: Persistencia de Plantilla Estándar y Configuración DJ en base de datos

## Estado
Aceptado

## Contexto

ADR-0006 definió un MVP donde la plantilla estándar y la configuración de
Declaración Jurada se guardan en RAM por sesión. Esto genera dos problemas
operativos concretos:

1. Middle Office debe reconfigurar la plantilla y las reglas de DJ cada vez
   que el servidor se reinicia o la sesión expira.
2. Si dos pestañas del mismo usuario están abiertas, la configuración puede
   desincronizarse entre sesiones.

La plantilla y la config DJ son datos de configuración global del sistema
(no datos de operaciones), por lo que su persistencia no viola el principio
de ADR-0006 de no almacenar órdenes en DB.

Las Minutas siguen en RAM sin cambios (ADR-0006 §2 se mantiene).

## Decisiones

### 1. Dos nuevas tablas en DB

**Tabla `plantilla`**
```sql
id             INTEGER PRIMARY KEY  -- siempre 1 (único registro)
texto          TEXT NOT NULL
actualizado_en DATETIME NOT NULL
```

**Tabla `config_dj`**
```sql
id                      INTEGER PRIMARY KEY  -- siempre 1 (único registro)
activa                  BOOLEAN NOT NULL DEFAULT FALSE
incluir_texto_en_minuta BOOLEAN NOT NULL DEFAULT FALSE
texto_alerta            TEXT NOT NULL DEFAULT ''
reglas                  TEXT NOT NULL DEFAULT '[]'   -- JSON serializado
logica                  VARCHAR(3) NOT NULL DEFAULT 'OR'  -- 'OR' | 'AND'
actualizado_en          DATETIME NOT NULL
```

### 2. Patrón de registro único (upsert con id=1)

Ambas tablas tienen siempre exactamente un registro (id=1).
Las operaciones de escritura son siempre upsert: si no existe → INSERT,
si existe → UPDATE. No hay soft-delete ni historial de versiones.

Justificación: el sistema tiene un único operador (Middle Office).
Si se agregan roles en Fase 2, este diseño se extiende a múltiples registros
con FK al usuario.

### 3. La plantilla es el texto íntegro del mail

La plantilla reemplaza al generador hardcodeado `minuta_generator.generate_minuta_text()`.
El texto guardado en DB es el mail completo con variables interpoladas.
Middle Office tiene control total sobre el formato, el orden de los campos
y el tono del mensaje.

**Variables disponibles en la plantilla:**

| Variable | Descripción |
|---|---|
| `{cliente_nombre}` | Nombre del cliente |
| `{cuenta_comitente}` | Número de cuenta comitente |
| `{cuenta_cotapartista}` | Número de cuenta cotapartista |
| `{instrumento}` | Instrumento financiero |
| `{tipo}` | Tipo de operación (COMPRA / VENTA) |
| `{cantidad}` | Cantidad de títulos |
| `{precio}` | Precio unitario |
| `{moneda}` | Moneda (ARS / USD / etc.) |
| `{liquidacion}` | Condición de liquidación (CI / 24HS / 48HS) |
| `{fecha_operacion}` | Fecha y hora de la operación |

> Cuando el broker provea el archivo Excel modelo, se actualizará esta lista
> si aparecen campos nuevos (ej: `mercado`, `numero_operacion`, `importe`).
> Ver pendiente en CLAUDE.md.

**Texto default** (usado cuando no existe registro en DB y como punto de
partida para nuevas instalaciones):

```
MINUTA DE OPERACIÓN
Fecha y hora: {fecha_operacion}

Cliente: {cliente_nombre}
Cuenta Comitente: {cuenta_comitente}
Cuenta Cotapartista: {cuenta_cotapartista}

DETALLE DE LA OPERACIÓN
Instrumento: {instrumento}
Tipo: {tipo}
Cantidad: {cantidad}
Precio: {precio} {moneda}
Condición de Liquidación: {liquidacion}

Quedo a su disposición ante cualquier consulta.
Saludos cordiales.
```

### 4. Interpolación de variables — seguridad

Las variables se reemplazan usando `string.Template.safe_substitute()`
con un diccionario de sustitución estrictamente controlado.

`safe_substitute` deja sin reemplazar cualquier token desconocido en lugar
de lanzar excepción — protege contra errores de tipeo en el template.

**Prohibido:** usar `str.format(**kwargs)` con texto del usuario — permite
acceso a atributos de objetos (`{obj.__class__}`) y es un vector de
inyección.

### 5. Declaración Jurada — tres modos de operación

El campo `incluir_texto_en_minuta` permite dos comportamientos distintos
cuando la DJ es detectada:

| `activa` | `incluir_texto_en_minuta` | Comportamiento |
|---|---|---|
| false | — | DJ desactivada. No se detecta ni avisa. |
| true | false | Solo aviso: minuta muestra ⚠ "Requiere DJ". Middle Office adjunta el documento DJ manualmente al mail. |
| true | true | Aviso + texto: minuta muestra ⚠ y agrega el `texto_alerta` interpolado con variables al final del cuerpo. Middle Office copia todo en un paso. |

El `texto_alerta` puede contener las mismas variables que la plantilla
(`{cliente_nombre}`, `{cantidad}`, `{moneda}`, etc.) y se interpola con
el mismo mecanismo `safe_substitute`.

### 6. Reglas de DJ — estructura JSON

`reglas` es un array JSON validado por Pydantic al escribir:

```json
[
  {"campo": "cantidad", "operador": ">=", "valor": "1000000"},
  {"campo": "moneda",   "operador": "=",  "valor": "USD"}
]
```

**Campos permitidos (whitelist):**
`cantidad`, `precio`, `moneda`, `liquidacion`, `tipo`, `instrumento`

**Operadores permitidos:** `>`, `<`, `=`, `!=`, `>=`, `<=`

Cualquier `campo` u `operador` fuera de la whitelist es rechazado con
HTTP 422 por el schema Pydantic. No se evalúan reglas con campos o
operadores no reconocidos.

### 7. Evaluación de reglas — lógica y tipos

- **`logica: "OR"`** (default): la DJ se activa si **alguna** regla se cumple.
- **`logica: "AND"`**: la DJ se activa solo si **todas** las reglas se cumplen.

**Coerción de tipos para comparación:**
- Campos numéricos (`cantidad`, `precio`): `valor` se convierte a `float`.
- Campos de texto (`moneda`, `liquidacion`, `tipo`, `instrumento`):
  comparación exacta case-insensitive.
- Si la conversión falla (ej: `valor="abc"` para campo numérico), la regla
  se evalúa como `False` sin lanzar excepción — protege la generación de
  minutas ante configuración inválida.

### 8. Carga en RAM al inicio de sesión

Al crear la sesión en `session_store`, el backend lee plantilla y config_dj
desde DB y los carga en `_SessionData`. Las actualizaciones vía
`PATCH /plantilla` y `PATCH /config/dj` escriben a DB **y** actualizan
el objeto en RAM de la sesión activa.

Si no existe registro en DB (primer uso), se usa la plantilla default
del §3 y config DJ con `activa=false`.

### 9. Endpoints — sin cambios de firma

Los endpoints existentes no cambian su contrato de API. Solo se extienden
los schemas:

| Endpoint | Comportamiento nuevo |
|---|---|
| `GET /plantilla` | Lee desde RAM (cargado de DB al inicio de sesión) |
| `PATCH /plantilla` | Escribe a DB + actualiza RAM |
| `GET /config/dj` | Lee desde RAM (cargado de DB al inicio de sesión) |
| `PATCH /config/dj` | Escribe a DB + actualiza RAM |

`ConfigDJSchema` se extiende con `incluir_texto_en_minuta`, `reglas`
y `logica`.

### 10. Frontend — editor de plantilla con botones de variables

La tab "Plantilla Estándar" agrega una barra de botones sobre el textarea,
uno por variable. Al hacer clic inserta el token `{nombre_variable}` en
la posición del cursor.

La tab "Config DJ" agrega:
- Toggle `activa` (existente).
- Toggle `incluir_texto_en_minuta` con descripción clara de cada modo.
- Textarea `texto_alerta` con la misma barra de variables que la plantilla.
- Panel de reglas: lista editable de condiciones campo/operador/valor.
  - Dropdown de campos limitado a la whitelist del §6.
  - Dropdown de operadores limitado a los del §6.
  - Input de valor (texto libre, validado al guardar).
- Selector de lógica OR / AND.

### 11. Migraciones Alembic

Se generan dos migraciones nuevas (una por tabla), compatibles con SQLite
(dev) y PostgreSQL (prod). El campo `reglas` se almacena como `Text`
(JSON serializado) en ambos motores.

## Consecuencias

**Positivo:**
- Plantilla y config DJ sobreviven reinicios del servidor.
- Middle Office no pierde configuración entre sesiones.
- Las reglas de DJ son auditables y configurables sin tocar código.
- El toggle `incluir_texto_en_minuta` da flexibilidad total: aviso simple
  o texto completo generado, según lo que necesite el broker.
- Seguridad mejorada: whitelist de campos y operadores, interpolación con
  `safe_substitute`.

**Negativo:**
- La plantilla como texto libre requiere que Middle Office entienda la
  sintaxis `{variable}` — riesgo de romper el template accidentalmente.
  Mitigación: botones de inserción en el editor y `safe_substitute` que
  deja tokens inválidos sin reemplazar en lugar de fallar.
- Pequeño costo de latencia en inicio de sesión (una query extra por tabla).

**Neutro:**
- Las Minutas siguen en RAM (ADR-0006 §2 no cambia).
- La máquina de estados BORRADOR → ENVIADO no cambia.
- Cuando el broker provea el Excel modelo real, se actualizan las variables
  disponibles sin cambio de arquitectura (ver CLAUDE.md — pendientes
  bloqueantes).

## ADRs relacionados

- ADR-0006: se extiende — DB pasa de 1 tabla (`users`) a 3 (`users`,
  `plantilla`, `config_dj`). El principio de no persistir órdenes
  se mantiene.
- ADR-0001: entrada vía Excel — sin cambios
- ADR-0003: stack FastAPI + React — sin cambios
- ADR-0004: auth — sin cambios
