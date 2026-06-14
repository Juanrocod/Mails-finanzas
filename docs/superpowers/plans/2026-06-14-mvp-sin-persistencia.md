# MVP sin persistencia de órdenes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adaptar el backend y el frontend al MVP (ADR-0006): minutas en RAM, solo dos estados (BORRADOR/ENVIADO), tabs Plantilla y Config DJ, sin audit trail ni DB de órdenes.

**Architecture:** El backend elimina todos los modelos de orden de la DB y los reemplaza con un store en memoria keyed por `user_id`. El frontend elimina tabs obsoletas (Aprobados, Confirmados, Alertas, Audit) y agrega PlantillaPage y ConfigDJPage.

**Tech Stack:** Python 3.12 + FastAPI + pytest / React 18 + TypeScript + TanStack Query v5 + shadcn/ui

---

## File Map

### Backend — creados
| Archivo | Responsabilidad |
|---|---|
| `backend/app/services/session_store.py` | Store en RAM: minutas, plantilla, config DJ por user_id |
| `backend/app/schemas/session.py` | Pydantic schemas MVP: MinutaSchema, UploadMVPResponse, PlantillaSchema, ConfigDJSchema |
| `backend/app/routers/session.py` | Endpoints GET/PATCH /session/minutas, /plantilla, /config/dj |
| `backend/tests/test_session_store.py` | Unit tests del store |
| `backend/tests/test_session_router.py` | Integration tests de los endpoints de sesión |

### Backend — modificados
| Archivo | Cambio |
|---|---|
| `backend/app/services/dj_engine.py` | Elimina DB; nueva firma: `get_dj_texto(activa, texto_alerta) -> str | None` |
| `backend/app/routers/uploads.py` | Reescrito: procesa Excel → guarda en session_store → retorna minutas |
| `backend/app/main.py` | Registra session router; elimina orders, dashboard, audit routers |
| `backend/tests/conftest.py` | Elimina imports de modelos obsoletos; actualiza fixture `seeded_borrador_minuta` |
| `backend/tests/test_dj_engine.py` | Reescrito para nueva firma (sin DB) |
| `backend/tests/test_uploads.py` | Actualiza asserts a nueva response shape |

### Backend — eliminados
`routers/orders.py`, `routers/dashboard.py`, `routers/audit.py`, `models/order.py`, `models/audit.py`, `schemas/audit.py`, `services/audit.py`, `services/orders.py`, `tests/test_audit.py`, `tests/test_audit_router.py`, `tests/test_dashboard.py`, `tests/test_orders.py`, `tests/test_orders_router.py`, `tests/test_integration.py`

### Frontend — creados
| Archivo | Responsabilidad |
|---|---|
| `frontend/src/services/plantilla.ts` | fetchPlantilla, guardarPlantilla |
| `frontend/src/services/configDJ.ts` | fetchConfigDJ, guardarConfigDJ |
| `frontend/src/hooks/useSession.ts` | usePlantilla, useConfigDJ, sus mutations |
| `frontend/src/pages/PlantillaPage.tsx` | Editor de plantilla de mail |
| `frontend/src/pages/ConfigDJPage.tsx` | Toggle DJ + textarea alerta |

### Frontend — modificados
| Archivo | Cambio |
|---|---|
| `frontend/src/types/domain.ts` | MVP types: Minuta, ConfigDJ, Plantilla; elimina Orden, AuditEvent, etc. |
| `frontend/src/services/minutas.ts` | Apunta a /session/minutas; elimina aprobar/confirmar |
| `frontend/src/hooks/useMinutas.ts` | Elimina useAprobarMinuta, useRegistrarConfirmacion, useMarcarEnviada → useMarcarEnviado |
| `frontend/src/components/layout/Sidebar.tsx` | Nav MVP: Borradores, Enviados, Plantilla, Config DJ |
| `frontend/src/components/minutas/MinutaCard.tsx` | Usa tipo Minuta, elimina lógica ALERTA |
| `frontend/src/components/minutas/MinutaDrawer.tsx` | Acciones MVP: Guardar/Copiar/Enviado; elimina Aprobar/Confirmar/AuditTrail |
| `frontend/src/pages/DashboardPage.tsx` | ESTADO_TITULO MVP; usa tipo Minuta |
| `frontend/src/App.tsx` | Rutas MVP; agrega PlantillaPage, ConfigDJPage |

### Frontend — eliminados
`pages/AuditPage.tsx`, `components/minutas/AuditTrailSection.tsx`, `services/audit.ts`

---

## Task 1: session_store.py — Store en RAM

**Files:**
- Create: `backend/app/services/session_store.py`
- Test: `backend/tests/test_session_store.py`

- [ ] **Step 1.1: Escribir los tests que fallan**

```python
# backend/tests/test_session_store.py
import pytest
from datetime import datetime
from app.services.session_store import (
    get_session,
    clear_session,
    add_minutas,
    get_minutas,
    get_minuta,
    update_minuta_texto,
    marcar_enviada,
    get_plantilla,
    set_plantilla,
    get_config_dj,
    set_config_dj,
    MinutaSession,
    DEFAULT_PLANTILLA,
)


def _make_minuta(**kwargs) -> MinutaSession:
    defaults = dict(
        id="m1",
        cliente_nombre="Juan Pérez",
        cliente_email="juan@test.com",
        cuenta_comitente="12345",
        cuenta_cotapartista="67890",
        instrumento="AL30",
        tipo="COMPRA",
        cantidad=100.0,
        precio=70.5,
        moneda="USD",
        liquidacion="24HS",
        fecha_operacion=datetime(2026, 6, 14, 10, 0),
        dj_aplicada=False,
        dj_texto=None,
        estado="BORRADOR",
        texto_minuta="texto de prueba",
        texto_editado=False,
        creado_en=datetime(2026, 6, 14, 10, 0),
    )
    defaults.update(kwargs)
    return MinutaSession(**defaults)


USER = "user-abc"


@pytest.fixture(autouse=True)
def limpia_store():
    clear_session(USER)
    yield
    clear_session(USER)


def test_get_session_returns_empty_by_default():
    assert get_minutas(USER, "BORRADOR") == []


def test_add_minutas_stores_them():
    m = _make_minuta()
    add_minutas(USER, [m])
    result = get_minutas(USER, "BORRADOR")
    assert len(result) == 1
    assert result[0].id == "m1"


def test_get_minutas_filters_by_estado():
    m_borrador = _make_minuta(id="b1", estado="BORRADOR")
    m_enviado = _make_minuta(id="e1", estado="ENVIADO")
    add_minutas(USER, [m_borrador, m_enviado])
    assert [m.id for m in get_minutas(USER, "BORRADOR")] == ["b1"]
    assert [m.id for m in get_minutas(USER, "ENVIADO")] == ["e1"]


def test_get_minuta_by_id():
    m = _make_minuta(id="x99")
    add_minutas(USER, [m])
    found = get_minuta(USER, "x99")
    assert found is not None
    assert found.id == "x99"


def test_get_minuta_unknown_id_returns_none():
    assert get_minuta(USER, "no-existe") is None


def test_update_minuta_texto():
    m = _make_minuta(id="u1")
    add_minutas(USER, [m])
    updated = update_minuta_texto(USER, "u1", "nuevo texto")
    assert updated is not None
    assert updated.texto_minuta == "nuevo texto"
    assert updated.texto_editado is True


def test_update_minuta_texto_unknown_returns_none():
    assert update_minuta_texto(USER, "nope", "x") is None


def test_marcar_enviada_changes_estado():
    m = _make_minuta(id="v1")
    add_minutas(USER, [m])
    updated = marcar_enviada(USER, "v1")
    assert updated is not None
    assert updated.estado == "ENVIADO"


def test_marcar_enviada_unknown_returns_none():
    assert marcar_enviada(USER, "nope") is None


def test_plantilla_default():
    txt = get_plantilla(USER)
    assert txt == DEFAULT_PLANTILLA


def test_set_plantilla():
    set_plantilla(USER, "nueva plantilla")
    assert get_plantilla(USER) == "nueva plantilla"


def test_config_dj_default():
    cfg = get_config_dj(USER)
    assert cfg.activa is False
    assert cfg.texto_alerta == ""


def test_set_config_dj():
    set_config_dj(USER, activa=True, texto_alerta="Declaración requerida")
    cfg = get_config_dj(USER)
    assert cfg.activa is True
    assert cfg.texto_alerta == "Declaración requerida"


def test_clear_session_resets_everything():
    m = _make_minuta()
    add_minutas(USER, [m])
    set_plantilla(USER, "algo")
    set_config_dj(USER, activa=True, texto_alerta="algo")
    clear_session(USER)
    assert get_minutas(USER, "BORRADOR") == []
    assert get_plantilla(USER) == DEFAULT_PLANTILLA
    assert get_config_dj(USER).activa is False
```

- [ ] **Step 1.2: Correr los tests y verificar que fallan**

```
cd backend
venv\Scripts\pytest tests/test_session_store.py -v
```
Expected: `ModuleNotFoundError` — session_store no existe.

- [ ] **Step 1.3: Implementar session_store.py**

```python
# backend/app/services/session_store.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

DEFAULT_PLANTILLA = (
    "Estimado/a {cliente_nombre},\n\n"
    "Nos complace confirmar la operación realizada en el día de hoy.\n\n"
    "Quedamos a su disposición ante cualquier consulta.\n\n"
    "Saludos cordiales."
)


@dataclass
class MinutaSession:
    id: str
    cliente_nombre: str
    cliente_email: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    instrumento: str
    tipo: str
    cantidad: float
    precio: float
    moneda: str
    liquidacion: str
    fecha_operacion: datetime
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


@dataclass
class _ConfigDJ:
    activa: bool = False
    texto_alerta: str = ""


@dataclass
class _SessionData:
    minutas: list[MinutaSession] = field(default_factory=list)
    plantilla: str = field(default_factory=lambda: DEFAULT_PLANTILLA)
    config_dj: _ConfigDJ = field(default_factory=_ConfigDJ)


_store: dict[str, _SessionData] = {}


def _get_or_create(user_id: str) -> _SessionData:
    if user_id not in _store:
        _store[user_id] = _SessionData()
    return _store[user_id]


def get_session(user_id: str) -> _SessionData:
    return _get_or_create(user_id)


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)


def add_minutas(user_id: str, minutas: list[MinutaSession]) -> None:
    _get_or_create(user_id).minutas.extend(minutas)


def get_minutas(user_id: str, estado: str) -> list[MinutaSession]:
    return [m for m in _get_or_create(user_id).minutas if m.estado == estado]


def get_minuta(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    for m in _get_or_create(user_id).minutas:
        if m.id == minuta_id:
            return m
    return None


def update_minuta_texto(user_id: str, minuta_id: str, texto: str) -> Optional[MinutaSession]:
    m = get_minuta(user_id, minuta_id)
    if m is None:
        return None
    m.texto_minuta = texto
    m.texto_editado = True
    return m


def marcar_enviada(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    m = get_minuta(user_id, minuta_id)
    if m is None:
        return None
    m.estado = "ENVIADO"
    return m


def get_plantilla(user_id: str) -> str:
    return _get_or_create(user_id).plantilla


def set_plantilla(user_id: str, texto: str) -> None:
    _get_or_create(user_id).plantilla = texto


def get_config_dj(user_id: str) -> _ConfigDJ:
    return _get_or_create(user_id).config_dj


def set_config_dj(user_id: str, activa: bool, texto_alerta: str) -> None:
    _get_or_create(user_id).config_dj = _ConfigDJ(activa=activa, texto_alerta=texto_alerta)
```

- [ ] **Step 1.4: Correr los tests y verificar que pasan**

```
cd backend
venv\Scripts\pytest tests/test_session_store.py -v
```
Expected: 16 tests PASSED.

- [ ] **Step 1.5: Commit**

```
git add backend/app/services/session_store.py backend/tests/test_session_store.py
git commit -m "feat(backend): add in-memory session_store for MVP"
```

---

## Task 2: schemas/session.py — Schemas Pydantic MVP

**Files:**
- Create: `backend/app/schemas/session.py`

- [ ] **Step 2.1: Crear el archivo de schemas**

```python
# backend/app/schemas/session.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MinutaSchema(BaseModel):
    id: str
    cliente_nombre: str
    cliente_email: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    instrumento: str
    tipo: str
    cantidad: float
    precio: float
    moneda: str
    liquidacion: str
    fecha_operacion: datetime
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


class SessionMinutasResponse(BaseModel):
    items: List[MinutaSchema]
    total: int


class RowErrorSchema(BaseModel):
    fila: int
    mensaje: str


class UploadMVPResponse(BaseModel):
    nombre_archivo: str
    total_ordenes: int
    ordenes_validas: int
    ordenes_con_error: int
    errors: List[RowErrorSchema]
    minutas: List[MinutaSchema]


class EditTextoRequest(BaseModel):
    texto_minuta: str


class PlantillaSchema(BaseModel):
    texto: str


class ConfigDJSchema(BaseModel):
    activa: bool
    texto_alerta: str
```

- [ ] **Step 2.2: Verificar que el módulo importa sin errores**

```
cd backend
venv\Scripts\python -c "from app.schemas.session import MinutaSchema, UploadMVPResponse, PlantillaSchema, ConfigDJSchema; print('OK')"
```
Expected: `OK`

- [ ] **Step 2.3: Commit**

```
git add backend/app/schemas/session.py
git commit -m "feat(backend): add MVP Pydantic schemas (session.py)"
```

---

## Task 3: dj_engine.py — Refactor sin DB

**Files:**
- Modify: `backend/app/services/dj_engine.py`
- Modify: `backend/tests/test_dj_engine.py`

- [ ] **Step 3.1: Reescribir test_dj_engine.py sin DB**

```python
# backend/tests/test_dj_engine.py
from app.services.dj_engine import get_dj_texto


def test_returns_none_when_inactive():
    result = get_dj_texto(activa=False, texto_alerta="Texto DJ")
    assert result is None


def test_returns_texto_when_active():
    result = get_dj_texto(activa=True, texto_alerta="Declaración requerida por CNV")
    assert result == "Declaración requerida por CNV"


def test_returns_empty_string_when_active_but_no_text():
    result = get_dj_texto(activa=True, texto_alerta="")
    assert result == ""
```

- [ ] **Step 3.2: Correr y verificar que fallan (nueva firma no existe aún)**

```
cd backend
venv\Scripts\pytest tests/test_dj_engine.py -v
```
Expected: FAILED — `ImportError: cannot import name 'get_dj_texto'`

- [ ] **Step 3.3: Reescribir dj_engine.py**

```python
# backend/app/services/dj_engine.py
from typing import Optional


def get_dj_texto(activa: bool, texto_alerta: str) -> Optional[str]:
    """Return the DJ alert text if DJ is active, otherwise None."""
    return texto_alerta if activa else None
```

- [ ] **Step 3.4: Correr y verificar que pasan**

```
cd backend
venv\Scripts\pytest tests/test_dj_engine.py -v
```
Expected: 3 tests PASSED.

- [ ] **Step 3.5: Commit**

```
git add backend/app/services/dj_engine.py backend/tests/test_dj_engine.py
git commit -m "refactor(backend): simplify dj_engine — config from RAM, no DB"
```

---

## Task 4: uploads.py — Reescribir para RAM

**Files:**
- Modify: `backend/app/routers/uploads.py`
- Modify: `backend/tests/test_uploads.py`

- [ ] **Step 4.1: Reescribir test_uploads.py**

```python
# backend/tests/test_uploads.py
import io
import openpyxl
from datetime import datetime
from app.services.excel_parser import EXPECTED_COLUMNS
import app.services.session_store as store


def make_excel_bytes(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = list(EXPECTED_COLUMNS.values())
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    for row_idx, row in enumerate(rows, 2):
        for col_idx, key in enumerate(EXPECTED_COLUMNS.keys(), 1):
            ws.cell(row=row_idx, column=col_idx, value=row[key])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


VALID_ROW = {
    "cliente_nombre": "Ana García",
    "cliente_email": "ana@broker.com",
    "cuenta_comitente": "11111",
    "cuenta_cotapartista": "22222",
    "instrumento": "AL30",
    "tipo": "COMPRA",
    "cantidad": 100.0,
    "precio": 70.5,
    "moneda": "USD",
    "liquidacion": "24HS",
    "fecha_operacion": datetime(2026, 6, 14, 10, 30),
}


def test_upload_returns_201_and_minutas(client, auth_headers):
    excel = make_excel_bytes([VALID_ROW])
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["ordenes_validas"] == 1
    assert data["ordenes_con_error"] == 0
    assert len(data["minutas"]) == 1
    minuta = data["minutas"][0]
    assert minuta["cliente_nombre"] == "Ana García"
    assert minuta["estado"] == "BORRADOR"
    assert minuta["texto_minuta"] != ""
    assert "id" in minuta


def test_upload_two_rows_creates_two_minutas(client, auth_headers):
    row2 = {**VALID_ROW, "cliente_nombre": "Pedro López", "cliente_email": "pedro@broker.com"}
    excel = make_excel_bytes([VALID_ROW, row2])
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["ordenes_validas"] == 2
    assert len(r.json()["minutas"]) == 2


def test_upload_bad_extension_returns_400(client, auth_headers):
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.csv", b"a,b,c", "text/csv")},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_upload_missing_column_returns_400(client, auth_headers):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.cell(row=1, column=1, value="Columna Incorrecta")
    ws.cell(row=2, column=1, value="valor")
    buf = io.BytesIO()
    wb.save(buf)
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_upload_requires_auth(client):
    excel = make_excel_bytes([VALID_ROW])
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert r.status_code == 403


def test_partial_errors_reported_without_blocking(client, auth_headers):
    bad_row = {**VALID_ROW, "tipo": "INVALIDO"}
    excel = make_excel_bytes([VALID_ROW, bad_row])
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["ordenes_validas"] == 1
    assert data["ordenes_con_error"] == 1
    assert len(data["errors"]) == 1
    assert len(data["minutas"]) == 1
```

- [ ] **Step 4.2: Reescribir uploads.py**

```python
# backend/app/routers/uploads.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.session import UploadMVPResponse, RowErrorSchema, MinutaSchema
from app.services.dj_engine import get_dj_texto
from app.services.excel_parser import parse_excel_file
from app.services.minuta_generator import generate_minuta_text
from app.services import session_store
from app.services.session_store import MinutaSession

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post("/excel", response_model=UploadMVPResponse, status_code=status.HTTP_201_CREATED)
def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Se esperaba .xlsx o .xls, se recibió: '{ext}'",
        )

    file_bytes = file.file.read()

    try:
        parse_result = parse_excel_file(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_id = str(current_user.id)
    config = session_store.get_config_dj(user_id)
    dj_texto = get_dj_texto(config.activa, config.texto_alerta)
    now = datetime.now(timezone.utc)

    minutas: list[MinutaSession] = []
    for parsed in parse_result.ordenes:
        texto = generate_minuta_text(
            cliente_nombre=parsed.cliente_nombre,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            instrumento=parsed.instrumento,
            tipo=parsed.tipo,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            moneda=parsed.moneda,
            liquidacion=parsed.liquidacion,
            fecha_operacion=parsed.fecha_operacion,
            dj_texto=dj_texto,
        )
        minutas.append(MinutaSession(
            id=str(uuid.uuid4()),
            cliente_nombre=parsed.cliente_nombre,
            cliente_email=parsed.cliente_email,
            cuenta_comitente=parsed.cuenta_comitente,
            cuenta_cotapartista=parsed.cuenta_cotapartista,
            instrumento=parsed.instrumento,
            tipo=parsed.tipo,
            cantidad=parsed.cantidad,
            precio=parsed.precio,
            moneda=parsed.moneda,
            liquidacion=parsed.liquidacion,
            fecha_operacion=parsed.fecha_operacion,
            dj_aplicada=config.activa,
            dj_texto=dj_texto,
            estado="BORRADOR",
            texto_minuta=texto,
            texto_editado=False,
            creado_en=now,
        ))

    session_store.add_minutas(user_id, minutas)

    return UploadMVPResponse(
        nombre_archivo=filename,
        total_ordenes=len(parse_result.ordenes) + len(parse_result.errors),
        ordenes_validas=len(parse_result.ordenes),
        ordenes_con_error=len(parse_result.errors),
        errors=[RowErrorSchema(fila=e.fila, mensaje=e.mensaje) for e in parse_result.errors],
        minutas=[MinutaSchema(**m.__dict__) for m in minutas],
    )
```

- [ ] **Step 4.3: Correr los tests del upload**

```
cd backend
venv\Scripts\pytest tests/test_uploads.py -v
```
Expected: todos PASSED.

- [ ] **Step 4.4: Commit**

```
git add backend/app/routers/uploads.py backend/tests/test_uploads.py
git commit -m "refactor(backend): rewrite uploads — process Excel to RAM, return minutas"
```

---

## Task 5: routers/session.py — Endpoints de sesión

**Files:**
- Create: `backend/app/routers/session.py`
- Create: `backend/tests/test_session_router.py`

- [ ] **Step 5.1: Escribir tests del router de sesión**

```python
# backend/tests/test_session_router.py
import io, openpyxl
from datetime import datetime
from app.services.excel_parser import EXPECTED_COLUMNS
import app.services.session_store as store


def _upload_excel(client, auth_headers):
    """Helper: sube un Excel de una fila y retorna la lista de minutas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = list(EXPECTED_COLUMNS.values())
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    row = {
        "cliente_nombre": "Test User",
        "cliente_email": "test@broker.com",
        "cuenta_comitente": "12345",
        "cuenta_cotapartista": "67890",
        "instrumento": "GD30",
        "tipo": "VENTA",
        "cantidad": 50.0,
        "precio": 80.0,
        "moneda": "ARS",
        "liquidacion": "CI",
        "fecha_operacion": datetime(2026, 6, 14, 9, 0),
    }
    for col_idx, key in enumerate(EXPECTED_COLUMNS.keys(), 1):
        ws.cell(row=2, column=col_idx, value=row[key])
    buf = io.BytesIO()
    wb.save(buf)
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["minutas"]


def test_get_minutas_borradores(client, auth_headers):
    _upload_excel(client, auth_headers)
    r = client.get("/session/minutas?estado=BORRADOR", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert all(m["estado"] == "BORRADOR" for m in data["items"])


def test_get_minutas_enviados_empty_initially(client, auth_headers):
    r = client.get("/session/minutas?estado=ENVIADO", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_patch_texto(client, auth_headers):
    minutas = _upload_excel(client, auth_headers)
    mid = minutas[0]["id"]
    r = client.patch(
        f"/session/minutas/{mid}/texto",
        json={"texto_minuta": "nuevo texto editado"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["texto_minuta"] == "nuevo texto editado"
    assert data["texto_editado"] is True


def test_patch_texto_unknown_id_returns_404(client, auth_headers):
    r = client.patch(
        "/session/minutas/no-existe/texto",
        json={"texto_minuta": "x"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_marcar_enviado(client, auth_headers):
    minutas = _upload_excel(client, auth_headers)
    mid = minutas[0]["id"]
    r = client.patch(f"/session/minutas/{mid}/enviado", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "ENVIADO"


def test_marcar_enviado_unknown_returns_404(client, auth_headers):
    r = client.patch("/session/minutas/no-existe/enviado", headers=auth_headers)
    assert r.status_code == 404


def test_get_plantilla_default(client, auth_headers):
    r = client.get("/plantilla", headers=auth_headers)
    assert r.status_code == 200
    assert "texto" in r.json()
    assert len(r.json()["texto"]) > 0


def test_patch_plantilla(client, auth_headers):
    r = client.patch("/plantilla", json={"texto": "Mi plantilla personalizada"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["texto"] == "Mi plantilla personalizada"
    r2 = client.get("/plantilla", headers=auth_headers)
    assert r2.json()["texto"] == "Mi plantilla personalizada"


def test_get_config_dj_default(client, auth_headers):
    r = client.get("/config/dj", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["activa"] is False
    assert r.json()["texto_alerta"] == ""


def test_patch_config_dj(client, auth_headers):
    r = client.patch(
        "/config/dj",
        json={"activa": True, "texto_alerta": "Adjuntar formulario DJ-1"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["activa"] is True
    r2 = client.get("/config/dj", headers=auth_headers)
    assert r2.json()["activa"] is True
    assert r2.json()["texto_alerta"] == "Adjuntar formulario DJ-1"


def test_requires_auth_session_minutas(client):
    r = client.get("/session/minutas?estado=BORRADOR")
    assert r.status_code == 403


def test_requires_auth_plantilla(client):
    r = client.get("/plantilla")
    assert r.status_code == 403
```

- [ ] **Step 5.2: Correr y verificar que fallan**

```
cd backend
venv\Scripts\pytest tests/test_session_router.py -v
```
Expected: FAILED — endpoints no existen.

- [ ] **Step 5.3: Crear routers/session.py**

```python
# backend/app/routers/session.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.session import (
    SessionMinutasResponse,
    MinutaSchema,
    EditTextoRequest,
    PlantillaSchema,
    ConfigDJSchema,
)
from app.services import session_store

router = APIRouter(tags=["session"])


@router.get("/session/minutas", response_model=SessionMinutasResponse)
def get_session_minutas(
    estado: str = "BORRADOR",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)
    minutas = session_store.get_minutas(user_id, estado)
    items = [MinutaSchema(**m.__dict__) for m in minutas]
    return SessionMinutasResponse(items=items, total=len(items))


@router.patch("/session/minutas/{minuta_id}/texto", response_model=MinutaSchema)
def patch_minuta_texto(
    minuta_id: str,
    body: EditTextoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.update_minuta_texto(str(current_user.id), minuta_id, body.texto_minuta)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.patch("/session/minutas/{minuta_id}/enviado", response_model=MinutaSchema)
def patch_minuta_enviado(
    minuta_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.marcar_enviada(str(current_user.id), minuta_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.get("/plantilla", response_model=PlantillaSchema)
def get_plantilla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    texto = session_store.get_plantilla(str(current_user.id))
    return PlantillaSchema(texto=texto)


@router.patch("/plantilla", response_model=PlantillaSchema)
def patch_plantilla(
    body: PlantillaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_store.set_plantilla(str(current_user.id), body.texto)
    return body


@router.get("/config/dj", response_model=ConfigDJSchema)
def get_config_dj(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = session_store.get_config_dj(str(current_user.id))
    return ConfigDJSchema(activa=cfg.activa, texto_alerta=cfg.texto_alerta)


@router.patch("/config/dj", response_model=ConfigDJSchema)
def patch_config_dj(
    body: ConfigDJSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_store.set_config_dj(str(current_user.id), body.activa, body.texto_alerta)
    return body
```

- [ ] **Step 5.4: Correr los tests y verificar que pasan**

```
cd backend
venv\Scripts\pytest tests/test_session_router.py -v
```
Expected: todos PASSED (el router aún no está registrado en main.py — se registra en Task 6).

> Nota: los tests en este paso fallarán con 404 hasta que main.py registre el router en Task 6. Es correcto ejecutar Task 6 antes de este paso si los tests fallan por ese motivo.

- [ ] **Step 5.5: Commit**

```
git add backend/app/routers/session.py backend/tests/test_session_router.py
git commit -m "feat(backend): add session router for in-memory minutas, plantilla, config DJ"
```

---

## Task 6: main.py + conftest + limpieza de archivos obsoletos

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Delete: múltiples archivos obsoletos (ver lista abajo)

- [ ] **Step 6.1: Actualizar main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routers import auth, uploads
from app.routers import session as session_router

limiter = Limiter(key_func=get_remote_address)

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

- [ ] **Step 6.2: Actualizar conftest.py**

```python
# backend/tests/conftest.py
import os
from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test_secret_key_minimum_32_characters_here_ok")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("TOTP_ISSUER", "GestionMailsTest")
os.environ.setdefault("RATELIMIT_ENABLED", "false")

import pytest
import pyotp
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import hash_password, generate_totp_secret
from app.models.user import User

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestingSessionLocal = sessionmaker(_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db(setup_test_database):
    session = _TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def client(db):
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
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


@pytest.fixture
def make_valid_excel():
    import io
    import openpyxl
    from datetime import datetime
    from app.services.excel_parser import EXPECTED_COLUMNS

    wb = openpyxl.Workbook()
    ws = wb.active
    headers = list(EXPECTED_COLUMNS.values())
    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=header)

    row = {
        "cliente_nombre": "Test Cliente",
        "cliente_email": "cliente@test.com",
        "cuenta_comitente": "12345",
        "cuenta_cotapartista": "67890",
        "instrumento": "AL30",
        "tipo": "COMPRA",
        "cantidad": 100.0,
        "precio": 70.50,
        "moneda": "USD",
        "liquidacion": "24HS",
        "fecha_operacion": datetime(2026, 6, 14, 10, 30),
    }
    for col_idx, key in enumerate(EXPECTED_COLUMNS.keys(), 1):
        ws.cell(row=2, column=col_idx, value=row[key])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def seeded_borrador_minuta(client, auth_headers, make_valid_excel):
    """Upload a valid Excel and return the UUID string of the first BORRADOR minuta."""
    r = client.post(
        "/uploads/excel",
        files={"file": ("ops.xlsx", make_valid_excel,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 201, f"Upload failed: {r.text}"
    minutas = r.json()["minutas"]
    assert len(minutas) >= 1
    return minutas[0]["id"]
```

- [ ] **Step 6.3: Eliminar archivos obsoletos del backend**

```bash
# Routers
rm backend/app/routers/orders.py
rm backend/app/routers/dashboard.py
rm backend/app/routers/audit.py

# Models
rm backend/app/models/order.py
rm backend/app/models/audit.py

# Schemas
rm backend/app/schemas/audit.py
rm backend/app/schemas/order.py

# Services
rm backend/app/services/audit.py
rm backend/app/services/orders.py

# Tests obsoletos
rm backend/tests/test_audit.py
rm backend/tests/test_audit_router.py
rm backend/tests/test_dashboard.py
rm backend/tests/test_orders.py
rm backend/tests/test_orders_router.py
rm backend/tests/test_integration.py
```

- [ ] **Step 6.4: Correr toda la suite del backend y verificar que pasa**

```
cd backend
venv\Scripts\pytest -v
```
Expected: tests que pasan son `test_auth`, `test_excel_parser`, `test_minuta_generator`, `test_security`, `test_session_store`, `test_dj_engine`, `test_uploads`, `test_session_router`. Sin imports rotos.

- [ ] **Step 6.5: Commit**

```
git add backend/app/main.py backend/tests/conftest.py
git add -u   # stages eliminaciones
git commit -m "refactor(backend): remove DB order models, wire session router, clean up obsolete files"
```

---

## Task 7: Frontend — types + services

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/services/minutas.ts`
- Create: `frontend/src/services/plantilla.ts`
- Create: `frontend/src/services/configDJ.ts`
- Delete: `frontend/src/services/audit.ts`

- [ ] **Step 7.1: Reescribir domain.ts**

```typescript
// frontend/src/types/domain.ts
export type EstadoMinuta = 'BORRADOR' | 'ENVIADO'
export type TipoOperacion = 'COMPRA' | 'VENTA'
export type Liquidacion = 'CI' | '24HS' | '48HS'

export interface Minuta {
  id: string
  cliente_nombre: string
  cliente_email: string
  cuenta_comitente: string
  cuenta_cotapartista: string
  instrumento: string
  tipo: TipoOperacion
  cantidad: number
  precio: number
  moneda: string
  liquidacion: Liquidacion
  fecha_operacion: string
  dj_aplicada: boolean
  dj_texto: string | null
  estado: EstadoMinuta
  texto_minuta: string
  texto_editado: boolean
  creado_en: string
}

export interface SessionMinutasResponse {
  items: Minuta[]
  total: number
}

export interface ConfigDJ {
  activa: boolean
  texto_alerta: string
}

export interface Plantilla {
  texto: string
}

export interface UploadResponse {
  nombre_archivo: string
  total_ordenes: number
  ordenes_validas: number
  ordenes_con_error: number
  errors: { fila: number; mensaje: string }[]
  minutas: Minuta[]
}

export interface LoginResponse {
  pending_token: string
  message: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
```

- [ ] **Step 7.2: Reescribir services/minutas.ts**

```typescript
// frontend/src/services/minutas.ts
import { api } from './api'
import type { SessionMinutasResponse, Minuta, EstadoMinuta } from '../types/domain'

export async function fetchMinutas(estado: EstadoMinuta): Promise<SessionMinutasResponse> {
  const res = await api.get<SessionMinutasResponse>('/session/minutas', {
    params: { estado },
  })
  return res.data
}

export async function editarTexto(minutaId: string, texto_minuta: string): Promise<Minuta> {
  const res = await api.patch<Minuta>(`/session/minutas/${minutaId}/texto`, { texto_minuta })
  return res.data
}

export async function marcarEnviado(minutaId: string): Promise<Minuta> {
  const res = await api.patch<Minuta>(`/session/minutas/${minutaId}/enviado`)
  return res.data
}
```

- [ ] **Step 7.3: Crear services/plantilla.ts**

```typescript
// frontend/src/services/plantilla.ts
import { api } from './api'
import type { Plantilla } from '../types/domain'

export async function fetchPlantilla(): Promise<Plantilla> {
  const res = await api.get<Plantilla>('/plantilla')
  return res.data
}

export async function guardarPlantilla(texto: string): Promise<Plantilla> {
  const res = await api.patch<Plantilla>('/plantilla', { texto })
  return res.data
}
```

- [ ] **Step 7.4: Crear services/configDJ.ts**

```typescript
// frontend/src/services/configDJ.ts
import { api } from './api'
import type { ConfigDJ } from '../types/domain'

export async function fetchConfigDJ(): Promise<ConfigDJ> {
  const res = await api.get<ConfigDJ>('/config/dj')
  return res.data
}

export async function guardarConfigDJ(config: ConfigDJ): Promise<ConfigDJ> {
  const res = await api.patch<ConfigDJ>('/config/dj', config)
  return res.data
}
```

- [ ] **Step 7.5: Eliminar services/audit.ts**

```
rm frontend/src/services/audit.ts
```

- [ ] **Step 7.6: Verificar que TypeScript compila sin errores**

```
cd frontend
npm run build 2>&1 | head -40
```
Expected: errores de TypeScript en archivos que aún usan los tipos viejos (`Orden`, `EstadoMinuta` con más valores, etc.) — estos se resuelven en tareas 8-11. Por ahora, solo verificar que `domain.ts` y los servicios no tienen errores internos.

- [ ] **Step 7.7: Commit**

```
git add frontend/src/types/domain.ts frontend/src/services/minutas.ts frontend/src/services/plantilla.ts frontend/src/services/configDJ.ts
git rm frontend/src/services/audit.ts
git commit -m "refactor(frontend): MVP types and services — session endpoints, plantilla, configDJ"
```

---

## Task 8: Frontend — hooks

**Files:**
- Modify: `frontend/src/hooks/useMinutas.ts`
- Create: `frontend/src/hooks/useSession.ts`

- [ ] **Step 8.1: Reescribir hooks/useMinutas.ts**

```typescript
// frontend/src/hooks/useMinutas.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchMinutas, editarTexto, marcarEnviado } from '../services/minutas'
import type { EstadoMinuta } from '../types/domain'

export function useMinutas(estado: EstadoMinuta) {
  return useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
  })
}

export function useEditarTexto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ minutaId, texto }: { minutaId: string; texto: string }) =>
      editarTexto(minutaId, texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR' as EstadoMinuta] })
    },
  })
}

export function useMarcarEnviado() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (minutaId: string) => marcarEnviado(minutaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR' as EstadoMinuta] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO' as EstadoMinuta] })
    },
  })
}
```

- [ ] **Step 8.2: Crear hooks/useSession.ts**

```typescript
// frontend/src/hooks/useSession.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPlantilla, guardarPlantilla } from '../services/plantilla'
import { fetchConfigDJ, guardarConfigDJ } from '../services/configDJ'
import type { ConfigDJ } from '../types/domain'

export function usePlantilla() {
  return useQuery({
    queryKey: ['plantilla'],
    queryFn: fetchPlantilla,
  })
}

export function useGuardarPlantilla() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (texto: string) => guardarPlantilla(texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plantilla'] })
    },
  })
}

export function useConfigDJ() {
  return useQuery({
    queryKey: ['config-dj'],
    queryFn: fetchConfigDJ,
  })
}

export function useGuardarConfigDJ() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: ConfigDJ) => guardarConfigDJ(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config-dj'] })
    },
  })
}
```

- [ ] **Step 8.3: Commit**

```
git add frontend/src/hooks/useMinutas.ts frontend/src/hooks/useSession.ts
git commit -m "refactor(frontend): simplify hooks for MVP — remove aprobar/confirmar, add useSession"
```

---

## Task 9: Frontend — Sidebar + App.tsx

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 9.1: Reescribir Sidebar.tsx**

```tsx
// frontend/src/components/layout/Sidebar.tsx
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Send, FileEdit, Settings2, Upload, LogOut } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { cn } from '../../lib/utils'
import { fetchMinutas } from '../../services/minutas'
import { useAuth } from '../../hooks/useAuth'
import ExcelUploadModal from '../upload/ExcelUploadModal'
import type { EstadoMinuta } from '../../types/domain'

function useBadgeCount(estado: EstadoMinuta): number {
  const { data } = useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
    staleTime: 30_000,
  })
  return data?.total ?? 0
}

function NavItem({
  to,
  label,
  icon: Icon,
  count,
}: {
  to: string
  label: string
  icon: React.ElementType
  count?: number
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors',
          isActive
            ? 'bg-slate-100 text-slate-900 font-medium'
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
        )
      }
    >
      <span className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" />
        {label}
      </span>
      {count != null && count > 0 && (
        <Badge variant="secondary" className="text-xs tabular-nums">
          {count}
        </Badge>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { handleLogout } = useAuth()
  const [uploadOpen, setUploadOpen] = useState(false)
  const borradores = useBadgeCount('BORRADOR')
  const enviados = useBadgeCount('ENVIADO')

  return (
    <>
      <aside className="w-60 h-screen flex flex-col bg-white border-r border-slate-200 shrink-0">
        <div className="px-4 py-5 border-b border-slate-100">
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <p className="text-xs text-slate-400 mt-0.5">Sistema bursátil CNV</p>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          <NavItem to="/dashboard/borradores" label="Borradores" icon={FileText} count={borradores} />
          <NavItem to="/dashboard/enviados" label="Enviados" icon={Send} count={enviados} />
          <Separator className="my-2" />
          <NavItem to="/dashboard/plantilla" label="Plantilla Estándar" icon={FileEdit} />
          <NavItem to="/dashboard/config-dj" label="Config DJ" icon={Settings2} />
        </nav>

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
      </aside>

      <ExcelUploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  )
}
```

- [ ] **Step 9.2: Reescribir App.tsx**

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import TwoFactorPage from './pages/TwoFactorPage'
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

- [ ] **Step 9.3: Commit**

```
git add frontend/src/components/layout/Sidebar.tsx frontend/src/App.tsx
git commit -m "refactor(frontend): MVP navigation — remove obsolete tabs, add Plantilla and Config DJ"
```

---

## Task 10: Frontend — MinutaCard + MinutaDrawer

**Files:**
- Modify: `frontend/src/components/minutas/MinutaCard.tsx`
- Modify: `frontend/src/components/minutas/MinutaDrawer.tsx`
- Delete: `frontend/src/components/minutas/AuditTrailSection.tsx`

- [ ] **Step 10.1: Actualizar MinutaCard.tsx**

```tsx
// frontend/src/components/minutas/MinutaCard.tsx
import type React from 'react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { AlertTriangle, PenLine } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Card } from '../ui/card'
import { cn } from '../../lib/utils'
import type { Minuta } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700 hover:bg-slate-100',
  ENVIADO: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
}

function formatPrecio(precio: number, moneda: string): string {
  try {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: moneda,
      minimumFractionDigits: 2,
    }).format(precio)
  } catch {
    return `${moneda} ${precio.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`
  }
}

interface Props {
  minuta: Minuta
  onClick: () => void
}

export default function MinutaCard({ minuta, onClick }: Props) {
  return (
    <Card
      role="button"
      tabIndex={0}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      className="p-4 cursor-pointer hover:shadow-md transition-all select-none"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-slate-900 truncate max-w-[200px]">
              {minuta.cliente_nombre}
            </span>
            <Badge
              variant="secondary"
              className={cn(
                'text-xs font-semibold shrink-0',
                minuta.tipo === 'COMPRA'
                  ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100'
                  : 'bg-red-100 text-red-700 hover:bg-red-100'
              )}
            >
              {minuta.tipo}
            </Badge>
            {minuta.dj_aplicada && (
              <AlertTriangle
                className="h-3.5 w-3.5 text-amber-500 shrink-0"
                aria-label="Con Declaración Jurada"
              />
            )}
            {minuta.texto_editado && (
              <PenLine
                className="h-3.5 w-3.5 text-amber-500 shrink-0"
                aria-label="Texto editado manualmente"
              />
            )}
          </div>

          <p className="text-sm text-slate-700">
            {minuta.instrumento} — {minuta.cantidad.toLocaleString('es-AR')} ×{' '}
            {formatPrecio(minuta.precio, minuta.moneda)} {minuta.moneda}
          </p>

          <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
            <span>Liq. {minuta.liquidacion}</span>
            <span>·</span>
            <span>
              {format(new Date(minuta.fecha_operacion), 'dd/MM/yyyy HH:mm', { locale: es })}
            </span>
          </div>
        </div>

        <Badge
          variant="secondary"
          className={cn('text-xs shrink-0 self-start mt-0.5', ESTADO_BADGE[minuta.estado])}
        >
          {minuta.estado}
        </Badge>
      </div>
    </Card>
  )
}
```

- [ ] **Step 10.2: Reescribir MinutaDrawer.tsx**

```tsx
// frontend/src/components/minutas/MinutaDrawer.tsx
import { useEffect, useState } from 'react'
import { Copy, PenLine, ChevronDown, AlertTriangle } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '../ui/sheet'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { Separator } from '../ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible'
import { cn } from '../../lib/utils'
import { useMarcarEnviado, useEditarTexto } from '../../hooks/useMinutas'
import type { Minuta } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700',
  ENVIADO: 'bg-yellow-100 text-yellow-800',
}

interface Props {
  minuta: Minuta | null
  onClose: () => void
}

export default function MinutaDrawer({ minuta, onClose }: Props) {
  const [texto, setTexto] = useState('')
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const marcarEnviado = useMarcarEnviado()
  const editarTexto = useEditarTexto()

  useEffect(() => {
    if (minuta) {
      setTexto(minuta.texto_minuta)
      setMutationError(null)
      setCopied(false)
    }
  }, [minuta?.id])

  const isLoading = marcarEnviado.isPending || editarTexto.isPending
  const isBorrador = minuta?.estado === 'BORRADOR'
  const textoModificado = texto !== minuta?.texto_minuta

  async function handleGuardar() {
    if (!minuta) return
    try {
      setMutationError(null)
      await editarTexto.mutateAsync({ minutaId: minuta.id, texto })
    } catch {
      setMutationError('Error al guardar la edición. Intentá de nuevo.')
    }
  }

  async function handleEnviado() {
    if (!minuta) return
    try {
      setMutationError(null)
      await marcarEnviado.mutateAsync(minuta.id)
      onClose()
    } catch {
      setMutationError('Error al marcar como enviada. Intentá de nuevo.')
    }
  }

  async function handleCopiar() {
    const textToCopy = isBorrador ? texto : (minuta?.texto_minuta ?? '')
    try {
      await navigator.clipboard.writeText(textToCopy)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard unavailable — silently ignore
    }
  }

  return (
    <Sheet open={minuta !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="right"
        className="w-[600px] sm:max-w-[600px] p-0 flex flex-col overflow-hidden"
      >
        {minuta && (
          <>
            <SheetHeader className="px-6 py-4 border-b border-slate-200 shrink-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <SheetTitle className="text-base font-semibold truncate">
                    {minuta.cliente_nombre}
                  </SheetTitle>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Comitente: {minuta.cuenta_comitente} · Cotapartista:{' '}
                    {minuta.cuenta_cotapartista}
                  </p>
                </div>
                <Badge
                  variant="secondary"
                  className={cn('shrink-0 text-xs', ESTADO_BADGE[minuta.estado])}
                >
                  {minuta.estado}
                </Badge>
              </div>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {/* Texto de la Minuta */}
              <section className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-slate-700">Texto de la Minuta</h3>
                  <div className="flex items-center gap-2">
                    {minuta.texto_editado && (
                      <span className="flex items-center gap-1 text-xs text-amber-600">
                        <PenLine className="h-3 w-3" />
                        Editado
                      </span>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 gap-1.5 text-xs"
                      onClick={handleCopiar}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      {copied ? 'Copiado' : 'Copiar contenido'}
                    </Button>
                  </div>
                </div>
                {isBorrador ? (
                  <Textarea
                    value={texto}
                    onChange={(e) => setTexto(e.target.value)}
                    rows={14}
                    className="font-mono text-xs resize-none"
                  />
                ) : (
                  <pre className="text-xs font-mono bg-slate-50 border border-slate-200 rounded-md p-3 whitespace-pre-wrap break-words max-h-80 overflow-y-auto">
                    {minuta.texto_minuta}
                  </pre>
                )}
              </section>

              {/* DJ section */}
              {minuta.dj_aplicada && minuta.dj_texto && (
                <>
                  <Separator />
                  <Collapsible>
                    <CollapsibleTrigger className="flex items-center justify-between w-full text-sm font-medium text-slate-700 hover:text-slate-900 py-1 group">
                      <span className="flex items-center gap-1.5">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        Declaración Jurada incluida
                      </span>
                      <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pt-2">
                      <pre className="text-xs text-slate-600 bg-amber-50 border border-amber-100 rounded p-2 whitespace-pre-wrap">
                        {minuta.dj_texto}
                      </pre>
                    </CollapsibleContent>
                  </Collapsible>
                </>
              )}

              {/* Acciones */}
              <Separator />
              <section className="space-y-3">
                <h3 className="text-sm font-medium text-slate-700">Acciones</h3>
                {mutationError && (
                  <p role="alert" className="text-xs text-red-600 bg-red-50 rounded px-2 py-1.5">
                    {mutationError}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {isBorrador && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleGuardar}
                        disabled={isLoading || !textoModificado}
                      >
                        Guardar edición
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleEnviado}
                        disabled={isLoading}
                      >
                        Enviado
                      </Button>
                    </>
                  )}
                  {minuta.estado === 'ENVIADO' && (
                    <p className="text-xs text-slate-500 py-1">
                      Minuta enviada. Podés copiar el contenido si necesitás reenviar.
                    </p>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 10.3: Eliminar AuditTrailSection.tsx**

```
rm frontend/src/components/minutas/AuditTrailSection.tsx
```

- [ ] **Step 10.4: Commit**

```
git add frontend/src/components/minutas/MinutaCard.tsx frontend/src/components/minutas/MinutaDrawer.tsx
git rm frontend/src/components/minutas/AuditTrailSection.tsx
git commit -m "refactor(frontend): MVP MinutaCard and MinutaDrawer — simplified states and actions"
```

---

## Task 11: Frontend — DashboardPage + nuevas páginas + limpieza

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/pages/PlantillaPage.tsx`
- Create: `frontend/src/pages/ConfigDJPage.tsx`
- Delete: `frontend/src/pages/AuditPage.tsx`

- [ ] **Step 11.1: Actualizar DashboardPage.tsx**

```tsx
// frontend/src/pages/DashboardPage.tsx
import { useState } from 'react'
import { Skeleton } from '../components/ui/skeleton'
import MinutaCard from '../components/minutas/MinutaCard'
import MinutaDrawer from '../components/minutas/MinutaDrawer'
import { useMinutas } from '../hooks/useMinutas'
import type { EstadoMinuta, Minuta } from '../types/domain'

const ESTADO_TITULO: Record<EstadoMinuta, string> = {
  BORRADOR: 'Borradores',
  ENVIADO: 'Enviados',
}

interface Props {
  estado: EstadoMinuta
}

export default function DashboardPage({ estado }: Props) {
  const { data, isLoading, isError } = useMinutas(estado)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selectedMinuta: Minuta | null = data?.items.find((m) => m.id === selectedId) ?? null

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-baseline gap-3">
        <h2 className="text-xl font-semibold text-slate-900">
          {ESTADO_TITULO[estado]}
        </h2>
        {data && (
          <span className="text-sm text-slate-400">
            {data.total} {data.total === 1 ? 'minuta' : 'minutas'}
          </span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            Error al cargar las minutas. Verificá tu conexión e intentá de nuevo.
          </p>
        </div>
      )}

      {data && data.items.length === 0 && !isLoading && (
        <div className="text-center py-16">
          <p className="text-sm text-slate-400">
            {estado === 'BORRADOR'
              ? 'No hay minutas en borrador. Subí un Excel para comenzar.'
              : 'No hay minutas enviadas aún.'}
          </p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((minuta) => (
            <MinutaCard
              key={minuta.id}
              minuta={minuta}
              onClick={() => setSelectedId(minuta.id)}
            />
          ))}
        </div>
      )}

      <MinutaDrawer
        minuta={selectedMinuta}
        onClose={() => setSelectedId(null)}
      />
    </div>
  )
}
```

- [ ] **Step 11.2: Crear PlantillaPage.tsx**

```tsx
// frontend/src/pages/PlantillaPage.tsx
import { useState, useEffect } from 'react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { usePlantilla, useGuardarPlantilla } from '../hooks/useSession'

export default function PlantillaPage() {
  const { data, isLoading } = usePlantilla()
  const guardar = useGuardarPlantilla()
  const [texto, setTexto] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) setTexto(data.texto)
  }, [data])

  async function handleGuardar() {
    try {
      await guardar.mutateAsync(texto)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado — el backend solo falla si no está autenticado
    }
  }

  const modificado = data ? texto !== data.texto : false

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Plantilla Estándar</h2>
        <p className="text-sm text-slate-500 mt-1">
          Texto base para las minutas de esta sesión. Los cambios se pierden al cerrar sesión.
        </p>
      </div>

      {isLoading ? (
        <div className="h-64 bg-slate-100 rounded animate-pulse" />
      ) : (
        <Textarea
          value={texto}
          onChange={(e) => { setTexto(e.target.value); setSaved(false) }}
          rows={18}
          className="font-mono text-sm resize-none"
          placeholder="Ingresá el texto de la plantilla estándar..."
        />
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={handleGuardar}
          disabled={guardar.isPending || !modificado}
        >
          {guardar.isPending ? 'Guardando...' : 'Guardar plantilla'}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">Guardado</span>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 11.3: Crear ConfigDJPage.tsx**

```tsx
// frontend/src/pages/ConfigDJPage.tsx
import { useState, useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { useConfigDJ, useGuardarConfigDJ } from '../hooks/useSession'

export default function ConfigDJPage() {
  const { data, isLoading } = useConfigDJ()
  const guardar = useGuardarConfigDJ()
  const [activa, setActiva] = useState(false)
  const [textoAlerta, setTextoAlerta] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setActiva(data.activa)
      setTextoAlerta(data.texto_alerta)
    }
  }, [data])

  async function handleGuardar() {
    try {
      await guardar.mutateAsync({ activa, texto_alerta: textoAlerta })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado
    }
  }

  const modificado = data
    ? activa !== data.activa || textoAlerta !== data.texto_alerta
    : false

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Configuración DJ</h2>
        <p className="text-sm text-slate-500 mt-1">
          Cuando la DJ está activa, se agrega el texto de alerta al final de cada minuta generada.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-10 bg-slate-100 rounded animate-pulse" />
          <div className="h-32 bg-slate-100 rounded animate-pulse" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Toggle DJ activa */}
          <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
            <button
              type="button"
              role="switch"
              aria-checked={activa}
              onClick={() => { setActiva(!activa); setSaved(false) }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
                activa ? 'bg-slate-800' : 'bg-slate-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  activa ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {activa ? 'DJ activa' : 'DJ inactiva'}
              </p>
              <p className="text-xs text-slate-500">
                {activa
                  ? 'El texto de alerta se incluirá en todas las minutas generadas'
                  : 'No se agrega ningún texto de DJ a las minutas'}
              </p>
            </div>
            {activa && <AlertTriangle className="h-4 w-4 text-amber-500 ml-auto shrink-0" />}
          </div>

          {/* Texto de alerta */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Texto de alerta DJ
            </label>
            <Textarea
              value={textoAlerta}
              onChange={(e) => { setTextoAlerta(e.target.value); setSaved(false) }}
              rows={8}
              disabled={!activa}
              className="font-mono text-sm resize-none disabled:opacity-50"
              placeholder="Ingresá el texto que aparecerá en la sección DJ de cada minuta..."
            />
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={handleGuardar}
          disabled={guardar.isPending || !modificado}
        >
          {guardar.isPending ? 'Guardando...' : 'Guardar configuración'}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">Guardado</span>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 11.4: Eliminar AuditPage.tsx**

```
rm frontend/src/pages/AuditPage.tsx
```

- [ ] **Step 11.5: Verificar que TypeScript compila sin errores**

```
cd frontend
npm run build
```
Expected: 0 errores de TypeScript. Si hay errores residuales, son por imports que no se actualizaron — buscar el símbolo en cuestión y actualizar el import.

- [ ] **Step 11.6: Commit**

```
git add frontend/src/pages/DashboardPage.tsx frontend/src/pages/PlantillaPage.tsx frontend/src/pages/ConfigDJPage.tsx
git rm frontend/src/pages/AuditPage.tsx
git commit -m "feat(frontend): MVP pages — DashboardPage simplified, PlantillaPage, ConfigDJPage"
```

---

## Task 12: Smoke test end-to-end y commit final

- [ ] **Step 12.1: Correr toda la suite del backend**

```
cd backend
venv\Scripts\pytest -v
```
Expected: todos los tests pasan.

- [ ] **Step 12.2: Levantar el servidor y probar manualmente**

```
cd backend
venv\Scripts\uvicorn app.main:app --reload --port 8000
```
En otra terminal:
```
cd frontend
npm run dev
```

- [ ] **Step 12.3: Checklist de smoke test manual**

1. Ir a `http://localhost:5173` → redirige a `/login`
2. Login con usuario/contraseña + TOTP → llega a `/dashboard/borradores`
3. Sidebar muestra: Borradores, Enviados, Plantilla Estándar, Config DJ
4. Click "Subir Excel" → modal de 4 pasos → subir un Excel válido → "X Minutas generadas" → cierra
5. Lista de borradores muestra las minutas generadas
6. Click en una minuta → drawer abre → texto editable → "Copiar contenido" copia al portapapeles
7. Click "Guardar edición" (con texto modificado) → ícono de lápiz aparece en la card
8. Click "Enviado" → minuta desaparece de Borradores → aparece en Enviados
9. Navegar a `/dashboard/plantilla` → textarea con texto por defecto → editar → Guardar
10. Navegar a `/dashboard/config-dj` → toggle OFF → activar → ingresar texto → Guardar
11. Subir otro Excel → verificar que las nuevas minutas tienen el texto DJ al final
12. Cerrar sesión → vuelve a `/login`

- [ ] **Step 12.4: Commit final de documentación actualizada**

```
git add docs/adr/0006-mvp-sin-persistencia.md docs/frontend-spec.md docs/superpowers/plans/2026-06-14-mvp-sin-persistencia.md CLAUDE.md .claude/rules/frontend.md
git commit -m "docs: update ADR-0006, frontend-spec, CLAUDE.md for MVP architecture"
```

---

## Self-Review

**Spec coverage check:**

| Requisito ADR-0006 | Tarea |
|---|---|
| DB solo para auth | Task 6 — eliminar models/order.py, models/audit.py |
| Órdenes en RAM | Task 1 — session_store.py |
| Upload retorna minutas | Task 4 — uploads.py |
| GET /session/minutas | Task 5 |
| PATCH /session/minutas/{id}/enviado | Task 5 |
| GET/PATCH /plantilla | Task 5 |
| GET/PATCH /config/dj | Task 5 |
| Estados BORRADOR/ENVIADO | Task 7 — domain.ts |
| Eliminar tabs APROBADO/CONFIRMADO/ALERTA/AUDIT | Task 9 — Sidebar + App.tsx |
| Botón "Copiar contenido" | Task 10 — MinutaDrawer |
| Botón "Enviado" | Task 10 — MinutaDrawer |
| Tab Plantilla Estándar | Task 11 |
| Tab Config DJ con toggle + textarea | Task 11 |
| Auth sin cambios | No tocado |
| Sin audit trail | Tasks 6, 10, 11 — eliminado |

**Type consistency check:**
- `MinutaSession` (session_store) → `MinutaSchema` (schemas/session.py) → `Minuta` (domain.ts) — campos idénticos en las tres capas ✓
- `get_dj_texto(activa, texto_alerta)` usado en `uploads.py` Task 4 ✓
- `useMarcarEnviado` (Task 8) llama a `marcarEnviado(minutaId)` de `minutas.ts` (Task 7) ✓
- `MinutaCard` recibe `minuta: Minuta` (Task 10), `DashboardPage` pasa `minuta={minuta}` (Task 11) ✓
- `MinutaDrawer` recibe `minuta: Minuta | null` (Task 10), `DashboardPage` pasa `minuta={selectedMinuta}` (Task 11) ✓
