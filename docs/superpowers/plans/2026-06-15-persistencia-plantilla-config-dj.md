# Persistencia Plantilla y Config DJ — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistir la plantilla de mail y la config de DJ en DB (tablas `plantilla` y `config_dj`), reemplazar el generador hardcodeado por interpolación de plantilla con variables, e implementar evaluación de reglas configurables por campo/operador/valor para detección de DJ.

**Architecture:** Se crean dos modelos SQLAlchemy con id=1 (registro único). Un nuevo servicio `db_config.py` centraliza las operaciones de lectura/escritura. Los routers de plantilla y config DJ dejan de usar `session_store` y usan `db_config` directamente. El `dj_engine` pasa de un toggle global a evaluación de reglas por orden. El `minuta_generator` reemplaza la generación hardcodeada por `str.format_map` con `_SafeDict` para interpolación segura.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic v2, React 18, TypeScript, TanStack Query v5, shadcn/ui, Tailwind CSS.

---

## Mapa de archivos

| Acción | Archivo |
|--------|---------|
| Crear | `backend/app/models/plantilla.py` |
| Crear | `backend/app/models/config_dj.py` |
| Crear | `backend/app/services/db_config.py` |
| Crear | `backend/alembic/versions/<rev>_add_plantilla_config_dj.py` |
| Crear | `backend/tests/test_dj_engine.py` |
| Crear | `backend/tests/test_minuta_generator.py` |
| Crear | `backend/tests/test_db_config.py` |
| Modificar | `backend/alembic/env.py` |
| Modificar | `backend/app/services/dj_engine.py` |
| Modificar | `backend/app/services/minuta_generator.py` |
| Modificar | `backend/app/services/session_store.py` |
| Modificar | `backend/app/schemas/session.py` |
| Modificar | `backend/app/routers/session.py` |
| Modificar | `backend/app/routers/uploads.py` |
| Modificar | `frontend/src/types/domain.ts` |
| Modificar | `frontend/src/services/configDJ.ts` |
| Modificar | `frontend/src/pages/PlantillaPage.tsx` |
| Modificar | `frontend/src/pages/ConfigDJPage.tsx` |

---

## Task 1: SQLAlchemy models + fix alembic/env.py

**Files:**
- Create: `backend/app/models/plantilla.py`
- Create: `backend/app/models/config_dj.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Crear model Plantilla**

```python
# backend/app/models/plantilla.py
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime
from app.core.database import Base


class Plantilla(Base):
    __tablename__ = "plantilla"
    id = Column(Integer, primary_key=True, default=1)
    texto = Column(Text, nullable=False)
    actualizado_en = Column(DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Crear model ConfigDJ**

```python
# backend/app/models/config_dj.py
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, Text, String, DateTime
from app.core.database import Base


class ConfigDJ(Base):
    __tablename__ = "config_dj"
    id = Column(Integer, primary_key=True, default=1)
    activa = Column(Boolean, nullable=False, default=False)
    incluir_texto_en_minuta = Column(Boolean, nullable=False, default=False)
    texto_alerta = Column(Text, nullable=False, default="")
    reglas = Column(Text, nullable=False, default="[]")   # JSON serializado
    logica = Column(String(3), nullable=False, default="OR")
    actualizado_en = Column(DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 3: Corregir alembic/env.py**

Reemplazar las importaciones que apuntan a modelos eliminados en master:

```python
# backend/alembic/env.py
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/plantilla.py backend/app/models/config_dj.py backend/alembic/env.py
git commit -m "feat(backend): add Plantilla and ConfigDJ SQLAlchemy models, fix alembic env imports"
```

---

## Task 2: Migración Alembic + crear tablas en dev.db

**Files:**
- Create: `backend/alembic/versions/0002_add_plantilla_config_dj.py`

- [ ] **Step 1: Crear archivo de migración**

```python
# backend/alembic/versions/0002_add_plantilla_config_dj.py
"""add plantilla and config_dj tables

Revision ID: 0002
Revises: ed7df405935c
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = 'ed7df405935c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plantilla',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'config_dj',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activa', sa.Boolean(), nullable=False),
        sa.Column('incluir_texto_en_minuta', sa.Boolean(), nullable=False),
        sa.Column('texto_alerta', sa.Text(), nullable=False),
        sa.Column('reglas', sa.Text(), nullable=False),
        sa.Column('logica', sa.String(length=3), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('config_dj')
    op.drop_table('plantilla')
```

- [ ] **Step 2: Crear tablas en dev.db (SQLite)**

Desde `backend/` con el venv activado. El dev.db fue creado por `init_dev_db.py` sin pasar por Alembic, así que usamos `create_all` directamente para las tablas nuevas:

```bash
cd backend
python -c "
import os, sys
os.environ['DATABASE_URL'] = 'sqlite:///./dev.db'
os.environ['SECRET_KEY'] = 'dev_secret_key_minimum_32_characters_here_change_in_prod'
os.environ['ENCRYPTION_KEY'] = 'LyWtB1layYFDFofxU8rPzytOeU9BJYQh6X1tstWHhD4='
sys.path.insert(0, '.')
from app.core.database import Base, engine
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ
Base.metadata.create_all(engine)
print('OK: tablas plantilla y config_dj creadas en dev.db')
"
```

Resultado esperado:
```
OK: tablas plantilla y config_dj creadas en dev.db
```

- [ ] **Step 3: Verificar que las tablas existen**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('dev.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print([t[0] for t in tables])
conn.close()
"
```

Resultado esperado: lista que incluye `plantilla` y `config_dj`.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/0002_add_plantilla_config_dj.py
git commit -m "feat(backend): migration 0002 — add plantilla and config_dj tables"
```

---

## Task 3: Servicio db_config.py

**Files:**
- Create: `backend/app/services/db_config.py`
- Create: `backend/tests/test_db_config.py`

- [ ] **Step 1: Escribir tests primero**

```python
# backend/tests/test_db_config.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ
from app.services import db_config
from app.services.db_config import ConfigDJData, DEFAULT_PLANTILLA


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    session = Session()
    yield session
    session.close()


def test_load_plantilla_returns_default_when_empty(db):
    result = db_config.load_plantilla(db)
    assert result == DEFAULT_PLANTILLA


def test_save_and_load_plantilla(db):
    db_config.save_plantilla(db, "Hola {cliente_nombre}")
    assert db_config.load_plantilla(db) == "Hola {cliente_nombre}"


def test_save_plantilla_upserts(db):
    db_config.save_plantilla(db, "primera")
    db_config.save_plantilla(db, "segunda")
    assert db_config.load_plantilla(db) == "segunda"
    assert db.query(Plantilla).count() == 1


def test_load_config_dj_returns_defaults_when_empty(db):
    cfg = db_config.load_config_dj(db)
    assert cfg.activa is False
    assert cfg.incluir_texto_en_minuta is False
    assert cfg.texto_alerta == ""
    assert cfg.reglas == []
    assert cfg.logica == "OR"


def test_save_and_load_config_dj(db):
    data = ConfigDJData(
        activa=True,
        incluir_texto_en_minuta=True,
        texto_alerta="DJ: {cliente_nombre}",
        reglas=[{"campo": "cantidad", "operador": ">=", "valor": "1000000"}],
        logica="AND",
    )
    db_config.save_config_dj(db, data)
    loaded = db_config.load_config_dj(db)
    assert loaded.activa is True
    assert loaded.incluir_texto_en_minuta is True
    assert loaded.texto_alerta == "DJ: {cliente_nombre}"
    assert loaded.reglas == [{"campo": "cantidad", "operador": ">=", "valor": "1000000"}]
    assert loaded.logica == "AND"


def test_save_config_dj_upserts(db):
    db_config.save_config_dj(db, ConfigDJData(activa=True))
    db_config.save_config_dj(db, ConfigDJData(activa=False))
    assert db_config.load_config_dj(db).activa is False
    assert db.query(ConfigDJ).count() == 1
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend
python -m pytest tests/test_db_config.py -v
```

Resultado esperado: `ImportError` o `ModuleNotFoundError` (el módulo no existe aún).

- [ ] **Step 3: Implementar db_config.py**

```python
# backend/app/services/db_config.py
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.plantilla import Plantilla
from app.models.config_dj import ConfigDJ

DEFAULT_PLANTILLA = (
    "MINUTA DE OPERACIÓN\n"
    "Fecha y hora: {fecha_operacion}\n\n"
    "Cliente: {cliente_nombre}\n"
    "Cuenta Comitente: {cuenta_comitente}\n"
    "Cuenta Cotapartista: {cuenta_cotapartista}\n\n"
    "DETALLE DE LA OPERACIÓN\n"
    "Instrumento: {instrumento}\n"
    "Tipo: {tipo}\n"
    "Cantidad: {cantidad}\n"
    "Precio: {precio} {moneda}\n"
    "Condición de Liquidación: {liquidacion}\n\n"
    "Quedo a su disposición ante cualquier consulta.\n"
    "Saludos cordiales."
)


@dataclass
class ConfigDJData:
    activa: bool = False
    incluir_texto_en_minuta: bool = False
    texto_alerta: str = ""
    reglas: list = field(default_factory=list)
    logica: str = "OR"


def load_plantilla(db: Session) -> str:
    row = db.get(Plantilla, 1)
    return row.texto if row else DEFAULT_PLANTILLA


def save_plantilla(db: Session, texto: str) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(Plantilla, 1)
    if row:
        row.texto = texto
        row.actualizado_en = now
    else:
        db.add(Plantilla(id=1, texto=texto, actualizado_en=now))
    db.commit()


def load_config_dj(db: Session) -> ConfigDJData:
    row = db.get(ConfigDJ, 1)
    if not row:
        return ConfigDJData()
    return ConfigDJData(
        activa=row.activa,
        incluir_texto_en_minuta=row.incluir_texto_en_minuta,
        texto_alerta=row.texto_alerta,
        reglas=json.loads(row.reglas),
        logica=row.logica,
    )


def save_config_dj(db: Session, data: ConfigDJData) -> None:
    now = datetime.now(timezone.utc)
    row = db.get(ConfigDJ, 1)
    if row:
        row.activa = data.activa
        row.incluir_texto_en_minuta = data.incluir_texto_en_minuta
        row.texto_alerta = data.texto_alerta
        row.reglas = json.dumps(data.reglas)
        row.logica = data.logica
        row.actualizado_en = now
    else:
        db.add(ConfigDJ(
            id=1,
            activa=data.activa,
            incluir_texto_en_minuta=data.incluir_texto_en_minuta,
            texto_alerta=data.texto_alerta,
            reglas=json.dumps(data.reglas),
            logica=data.logica,
            actualizado_en=now,
        ))
    db.commit()
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
python -m pytest tests/test_db_config.py -v
```

Resultado esperado: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/db_config.py backend/tests/test_db_config.py
git commit -m "feat(backend): add db_config service with ConfigDJData and load/save functions"
```

---

## Task 4: Reescribir dj_engine.py con evaluación de reglas

**Files:**
- Modify: `backend/app/services/dj_engine.py`
- Create: `backend/tests/test_dj_engine.py`

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_dj_engine.py
import pytest
from app.services.db_config import ConfigDJData
from app.services.dj_engine import evaluar_reglas, resolver_dj_texto

DATOS = {
    "cliente_nombre": "Juan Pérez",
    "cantidad": 1500000.0,
    "precio": 250.50,
    "moneda": "USD",
    "tipo": "COMPRA",
    "liquidacion": "48HS",
    "instrumento": "AL30",
}


def test_evaluar_inactiva_siempre_false():
    cfg = ConfigDJData(activa=False, reglas=[{"campo": "cantidad", "operador": ">=", "valor": "1000000"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_sin_reglas_false():
    cfg = ConfigDJData(activa=True, reglas=[])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_mayor_que_pasa():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">", "valor": "1000000"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_mayor_que_no_pasa():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">", "valor": "2000000"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_mayor_igual_pasa_exacto():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">=", "valor": "1500000"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_igual_texto():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "moneda", "operador": "=", "valor": "USD"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_igual_texto_case_insensitive():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "moneda", "operador": "=", "valor": "usd"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_distinto_texto():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "moneda", "operador": "!=", "valor": "ARS"}])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_or_una_cumple():
    cfg = ConfigDJData(activa=True, logica="OR", reglas=[
        {"campo": "cantidad", "operador": ">", "valor": "2000000"},
        {"campo": "moneda", "operador": "=", "valor": "USD"},
    ])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_and_ambas_cumplen():
    cfg = ConfigDJData(activa=True, logica="AND", reglas=[
        {"campo": "cantidad", "operador": ">=", "valor": "1000000"},
        {"campo": "moneda", "operador": "=", "valor": "USD"},
    ])
    assert evaluar_reglas(cfg, DATOS) is True


def test_evaluar_and_una_no_cumple():
    cfg = ConfigDJData(activa=True, logica="AND", reglas=[
        {"campo": "cantidad", "operador": ">=", "valor": "1000000"},
        {"campo": "moneda", "operador": "=", "valor": "ARS"},
    ])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_campo_invalido_es_false():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "CAMPO_RARO", "operador": ">", "valor": "0"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_evaluar_valor_no_numerico_es_false():
    cfg = ConfigDJData(activa=True, logica="OR",
                       reglas=[{"campo": "cantidad", "operador": ">", "valor": "abc"}])
    assert evaluar_reglas(cfg, DATOS) is False


def test_resolver_dj_texto_none_si_no_incluir():
    cfg = ConfigDJData(activa=True, incluir_texto_en_minuta=False, texto_alerta="DJ {cliente_nombre}")
    result = resolver_dj_texto(cfg, DATOS)
    assert result is None


def test_resolver_dj_texto_interpola_variables():
    cfg = ConfigDJData(activa=True, incluir_texto_en_minuta=True,
                       texto_alerta="Declara {cliente_nombre} por {moneda}")
    result = resolver_dj_texto(cfg, DATOS)
    assert result == "Declara Juan Pérez por USD"


def test_resolver_dj_texto_deja_variable_desconocida():
    cfg = ConfigDJData(activa=True, incluir_texto_en_minuta=True,
                       texto_alerta="Hola {variable_inexistente}")
    result = resolver_dj_texto(cfg, DATOS)
    assert result == "Hola {variable_inexistente}"
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
python -m pytest tests/test_dj_engine.py -v
```

Resultado esperado: fallos por firma incorrecta del módulo actual.

- [ ] **Step 3: Reescribir dj_engine.py**

```python
# backend/app/services/dj_engine.py
from typing import Optional
from app.services.db_config import ConfigDJData

_CAMPOS_NUMERICOS = {"cantidad", "precio"}
_CAMPOS_TEXTO = {"moneda", "liquidacion", "tipo", "instrumento"}
_CAMPOS_PERMITIDOS = _CAMPOS_NUMERICOS | _CAMPOS_TEXTO
_OPERADORES = {">", "<", "=", "!=", ">=", "<="}


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def evaluar_reglas(config: ConfigDJData, datos: dict) -> bool:
    if not config.activa or not config.reglas:
        return False

    resultados = []
    for regla in config.reglas:
        campo = regla.get("campo", "")
        operador = regla.get("operador", "")
        valor = regla.get("valor", "")

        if campo not in _CAMPOS_PERMITIDOS or operador not in _OPERADORES:
            resultados.append(False)
            continue

        valor_dato = datos.get(campo)

        if campo in _CAMPOS_NUMERICOS:
            try:
                v1 = float(valor_dato)
                v2 = float(valor)
            except (TypeError, ValueError):
                resultados.append(False)
                continue
            resultados.append(_cmp_num(v1, v2, operador))
        else:
            v1 = str(valor_dato or "").strip().upper()
            v2 = str(valor or "").strip().upper()
            resultados.append(_cmp_txt(v1, v2, operador))

    if not resultados:
        return False
    return any(resultados) if config.logica == "OR" else all(resultados)


def resolver_dj_texto(config: ConfigDJData, datos: dict) -> Optional[str]:
    if not config.incluir_texto_en_minuta or not config.texto_alerta:
        return None
    return config.texto_alerta.format_map(_SafeDict(datos)) or None


def _cmp_num(v1: float, v2: float, op: str) -> bool:
    if op == ">":  return v1 > v2
    if op == "<":  return v1 < v2
    if op == "=":  return v1 == v2
    if op == "!=": return v1 != v2
    if op == ">=": return v1 >= v2
    if op == "<=": return v1 <= v2
    return False


def _cmp_txt(v1: str, v2: str, op: str) -> bool:
    if op == "=":  return v1 == v2
    if op == "!=": return v1 != v2
    return False
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
python -m pytest tests/test_dj_engine.py -v
```

Resultado esperado: 17 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dj_engine.py backend/tests/test_dj_engine.py
git commit -m "feat(backend): rewrite dj_engine — rule evaluation with OR/AND logic, field whitelist"
```

---

## Task 5: Reescribir minuta_generator.py con interpolación de plantilla

**Files:**
- Modify: `backend/app/services/minuta_generator.py`
- Create: `backend/tests/test_minuta_generator.py`

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_minuta_generator.py
from datetime import datetime
from app.services.minuta_generator import generate_minuta_text, DEFAULT_PLANTILLA

FECHA = datetime(2026, 6, 15, 14, 30)
KWARGS = dict(
    plantilla=DEFAULT_PLANTILLA,
    cliente_nombre="Ana García",
    cuenta_comitente="12345",
    cuenta_cotapartista="67890",
    instrumento="GD30",
    tipo="VENTA",
    cantidad=500000.0,
    precio=1250.75,
    moneda="ARS",
    liquidacion="24HS",
    fecha_operacion=FECHA,
)


def test_genera_texto_con_nombre_cliente():
    texto = generate_minuta_text(**KWARGS)
    assert "Ana García" in texto


def test_genera_texto_con_instrumento():
    texto = generate_minuta_text(**KWARGS)
    assert "GD30" in texto


def test_formato_cantidad_punto_miles():
    texto = generate_minuta_text(**KWARGS)
    assert "500.000" in texto


def test_formato_precio_coma_decimal():
    texto = generate_minuta_text(**KWARGS)
    assert "1.250,75" in texto


def test_fecha_formateada():
    texto = generate_minuta_text(**KWARGS)
    assert "15/06/2026 14:30" in texto


def test_sin_dj_no_incluye_seccion_dj():
    texto = generate_minuta_text(**KWARGS)
    assert "DECLARACIÓN JURADA" not in texto


def test_con_dj_incluye_texto():
    texto = generate_minuta_text(**KWARGS, dj_texto="Declara no estar inhabilitado.")
    assert "DECLARACIÓN JURADA" in texto
    assert "Declara no estar inhabilitado." in texto


def test_plantilla_custom_usa_variables():
    plantilla = "Para: {cliente_nombre} | Instrumento: {instrumento}"
    texto = generate_minuta_text(**{**KWARGS, "plantilla": plantilla})
    assert texto == "Para: Ana García | Instrumento: GD30"


def test_variable_desconocida_queda_sin_reemplazar():
    plantilla = "Hola {cliente_nombre} {variable_rara}"
    texto = generate_minuta_text(**{**KWARGS, "plantilla": plantilla})
    assert "{variable_rara}" in texto
    assert "Ana García" in texto
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
python -m pytest tests/test_minuta_generator.py -v
```

Resultado esperado: varios FAILED (la firma actual no acepta `plantilla`).

- [ ] **Step 3: Reescribir minuta_generator.py**

```python
# backend/app/services/minuta_generator.py
from datetime import datetime
from typing import Optional


DEFAULT_PLANTILLA = (
    "MINUTA DE OPERACIÓN\n"
    "Fecha y hora: {fecha_operacion}\n\n"
    "Cliente: {cliente_nombre}\n"
    "Cuenta Comitente: {cuenta_comitente}\n"
    "Cuenta Cotapartista: {cuenta_cotapartista}\n\n"
    "DETALLE DE LA OPERACIÓN\n"
    "Instrumento: {instrumento}\n"
    "Tipo: {tipo}\n"
    "Cantidad: {cantidad}\n"
    "Precio: {precio} {moneda}\n"
    "Condición de Liquidación: {liquidacion}\n\n"
    "Quedo a su disposición ante cualquier consulta.\n"
    "Saludos cordiales."
)


class _SafeDict(dict):
    """Deja {variable} sin reemplazar si la clave no existe."""
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def generate_minuta_text(
    plantilla: str,
    cliente_nombre: str,
    cuenta_comitente: str,
    cuenta_cotapartista: str,
    instrumento: str,
    tipo: str,
    cantidad: float,
    precio: float,
    moneda: str,
    liquidacion: str,
    fecha_operacion: datetime,
    dj_texto: Optional[str] = None,
) -> str:
    cantidad_str = f"{cantidad:,.0f}".replace(",", ".")
    precio_str = (
        f"{precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    subs = _SafeDict(
        cliente_nombre=cliente_nombre,
        cuenta_comitente=cuenta_comitente,
        cuenta_cotapartista=cuenta_cotapartista,
        instrumento=instrumento,
        tipo=tipo,
        cantidad=cantidad_str,
        precio=precio_str,
        moneda=moneda,
        liquidacion=liquidacion,
        fecha_operacion=fecha_operacion.strftime("%d/%m/%Y %H:%M"),
    )
    texto = plantilla.format_map(subs)
    if dj_texto:
        texto += f"\n\n---\nDECLARACIÓN JURADA\n\n{dj_texto}"
    return texto
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
python -m pytest tests/test_minuta_generator.py -v
```

Resultado esperado: 9 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/minuta_generator.py backend/tests/test_minuta_generator.py
git commit -m "feat(backend): rewrite minuta_generator — template-based with SafeDict interpolation"
```

---

## Task 6: Limpiar session_store.py

**Files:**
- Modify: `backend/app/services/session_store.py`

Eliminar plantilla y config_dj del store. Solo quedan minutas.

- [ ] **Step 1: Reescribir session_store.py**

```python
# backend/app/services/session_store.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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
class _SessionData:
    minutas: list[MinutaSession] = field(default_factory=list)


_store: dict[str, _SessionData] = {}


def _get_or_create(user_id: str) -> _SessionData:
    if user_id not in _store:
        _store[user_id] = _SessionData()
    return _store[user_id]


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)


def clear_borradores(user_id: str) -> None:
    session = _get_or_create(user_id)
    session.minutas = [m for m in session.minutas if m.estado != "BORRADOR"]


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
```

- [ ] **Step 2: Correr todos los tests para verificar que nada se rompió**

```bash
python -m pytest tests/ -v
```

Resultado esperado: todos los tests previos siguen en PASSED.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/session_store.py
git commit -m "refactor(backend): remove plantilla and config_dj from session_store — now DB-only"
```

---

## Task 7: Actualizar schemas/session.py

**Files:**
- Modify: `backend/app/schemas/session.py`

- [ ] **Step 1: Reescribir schemas/session.py**

```python
# backend/app/schemas/session.py
from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import datetime

_CAMPOS_PERMITIDOS = {"cantidad", "precio", "moneda", "liquidacion", "tipo", "instrumento"}
_OPERADORES_PERMITIDOS = {">", "<", "=", "!=", ">=", "<="}


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


class ReglaDJSchema(BaseModel):
    campo: str
    operador: str
    valor: str

    @field_validator("campo")
    @classmethod
    def campo_valido(cls, v: str) -> str:
        if v not in _CAMPOS_PERMITIDOS:
            raise ValueError(
                f"campo '{v}' no permitido. Opciones: {sorted(_CAMPOS_PERMITIDOS)}"
            )
        return v

    @field_validator("operador")
    @classmethod
    def operador_valido(cls, v: str) -> str:
        if v not in _OPERADORES_PERMITIDOS:
            raise ValueError(
                f"operador '{v}' no permitido. Opciones: {sorted(_OPERADORES_PERMITIDOS)}"
            )
        return v


class ConfigDJSchema(BaseModel):
    activa: bool
    incluir_texto_en_minuta: bool
    texto_alerta: str
    reglas: List[ReglaDJSchema]
    logica: Literal["OR", "AND"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/session.py
git commit -m "feat(backend): extend schemas — ReglaDJSchema with validators, ConfigDJSchema with rules and logica"
```

---

## Task 8: Actualizar routers/session.py

**Files:**
- Modify: `backend/app/routers/session.py`

Los endpoints de plantilla y config/dj ahora leen/escriben en DB via `db_config`.

- [ ] **Step 1: Reescribir routers/session.py**

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
from app.services import db_config
from app.services.db_config import ConfigDJData

router = APIRouter(tags=["session"])


@router.get("/session/minutas", response_model=SessionMinutasResponse)
def get_session_minutas(
    estado: str = "BORRADOR",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    minutas = session_store.get_minutas(str(current_user.id), estado)
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
    return PlantillaSchema(texto=db_config.load_plantilla(db))


@router.patch("/plantilla", response_model=PlantillaSchema)
def patch_plantilla(
    body: PlantillaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_config.save_plantilla(db, body.texto)
    return body


@router.get("/config/dj", response_model=ConfigDJSchema)
def get_config_dj(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = db_config.load_config_dj(db)
    return ConfigDJSchema(
        activa=cfg.activa,
        incluir_texto_en_minuta=cfg.incluir_texto_en_minuta,
        texto_alerta=cfg.texto_alerta,
        reglas=cfg.reglas,
        logica=cfg.logica,
    )


@router.patch("/config/dj", response_model=ConfigDJSchema)
def patch_config_dj(
    body: ConfigDJSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_config.save_config_dj(db, ConfigDJData(
        activa=body.activa,
        incluir_texto_en_minuta=body.incluir_texto_en_minuta,
        texto_alerta=body.texto_alerta,
        reglas=[r.model_dump() for r in body.reglas],
        logica=body.logica,
    ))
    return body
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/session.py
git commit -m "feat(backend): session router — plantilla and config/dj now read/write DB via db_config"
```

---

## Task 9: Actualizar routers/uploads.py

**Files:**
- Modify: `backend/app/routers/uploads.py`

Usar `db_config` para leer plantilla y config DJ. Evaluar reglas por orden individual.

- [ ] **Step 1: Reescribir uploads.py**

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
from app.services import db_config, session_store
from app.services.dj_engine import evaluar_reglas, resolver_dj_texto
from app.services.excel_parser import parse_excel_file
from app.services.minuta_generator import generate_minuta_text
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
    config = db_config.load_config_dj(db)
    plantilla = db_config.load_plantilla(db)
    now = datetime.now(timezone.utc)

    minutas: list[MinutaSession] = []
    for parsed in parse_result.ordenes:
        datos_raw = {
            "cliente_nombre": parsed.cliente_nombre,
            "cantidad": parsed.cantidad,
            "precio": parsed.precio,
            "moneda": parsed.moneda,
            "tipo": parsed.tipo,
            "liquidacion": parsed.liquidacion,
            "instrumento": parsed.instrumento,
        }
        dj_aplica = evaluar_reglas(config, datos_raw)
        dj_texto = resolver_dj_texto(config, {
            "cliente_nombre": parsed.cliente_nombre,
            "cuenta_comitente": parsed.cuenta_comitente,
            "cuenta_cotapartista": parsed.cuenta_cotapartista,
            "instrumento": parsed.instrumento,
            "tipo": parsed.tipo,
            "cantidad": parsed.cantidad,
            "precio": parsed.precio,
            "moneda": parsed.moneda,
            "liquidacion": parsed.liquidacion,
            "fecha_operacion": parsed.fecha_operacion,
        }) if dj_aplica else None

        texto = generate_minuta_text(
            plantilla=plantilla,
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
            dj_aplicada=dj_aplica,
            dj_texto=dj_texto,
            estado="BORRADOR",
            texto_minuta=texto,
            texto_editado=False,
            creado_en=now,
        ))

    session_store.clear_borradores(user_id)
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

- [ ] **Step 2: Correr todos los tests backend**

```bash
python -m pytest tests/ -v
```

Resultado esperado: todos PASSED.

- [ ] **Step 3: Smoke test manual del backend**

Con el servidor corriendo (`uvicorn app.main:app --reload`):

```bash
curl http://localhost:8000/docs
```

Resultado esperado: 200 OK.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/uploads.py
git commit -m "feat(backend): uploads — load plantilla/config from DB, evaluate rules per order"
```

---

## Task 10: Frontend — tipos y servicios

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/services/configDJ.ts`

- [ ] **Step 1: Actualizar domain.ts**

```typescript
// frontend/src/types/domain.ts
export type EstadoMinuta = 'BORRADOR' | 'ENVIADO'
export type TipoOperacion = 'COMPRA' | 'VENTA'
export type Liquidacion = 'CI' | '24HS' | '48HS'
export type LogicaDJ = 'OR' | 'AND'
export type OperadorDJ = '>' | '<' | '=' | '!=' | '>=' | '<='
export type CampoDJ = 'cantidad' | 'precio' | 'moneda' | 'liquidacion' | 'tipo' | 'instrumento'

export interface ReglaDJ {
  campo: CampoDJ
  operador: OperadorDJ
  valor: string
}

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
  incluir_texto_en_minuta: boolean
  texto_alerta: string
  reglas: ReglaDJ[]
  logica: LogicaDJ
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

- [ ] **Step 2: Actualizar configDJ.ts**

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

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/domain.ts frontend/src/services/configDJ.ts
git commit -m "feat(frontend): add ReglaDJ, LogicaDJ, OperadorDJ types; extend ConfigDJ interface"
```

---

## Task 11: Frontend — PlantillaPage.tsx con botones de variables

**Files:**
- Modify: `frontend/src/pages/PlantillaPage.tsx`

- [ ] **Step 1: Reescribir PlantillaPage.tsx**

```tsx
// frontend/src/pages/PlantillaPage.tsx
import { useState, useEffect, useRef } from 'react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { usePlantilla, useGuardarPlantilla } from '../hooks/useSession'

const VARIABLES: { label: string; token: string }[] = [
  { label: 'Nombre cliente',    token: '{cliente_nombre}' },
  { label: 'Cta. comitente',    token: '{cuenta_comitente}' },
  { label: 'Cta. cotapartista', token: '{cuenta_cotapartista}' },
  { label: 'Instrumento',       token: '{instrumento}' },
  { label: 'Tipo',              token: '{tipo}' },
  { label: 'Cantidad',          token: '{cantidad}' },
  { label: 'Precio',            token: '{precio}' },
  { label: 'Moneda',            token: '{moneda}' },
  { label: 'Liquidación',       token: '{liquidacion}' },
  { label: 'Fecha operación',   token: '{fecha_operacion}' },
]

export default function PlantillaPage() {
  const { data, isLoading } = usePlantilla()
  const guardar = useGuardarPlantilla()
  const [texto, setTexto] = useState('')
  const [saved, setSaved] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (data) setTexto(data.texto)
  }, [data])

  function insertarVariable(token: string) {
    const el = textareaRef.current
    if (!el) return
    const start = el.selectionStart ?? texto.length
    const end = el.selectionEnd ?? texto.length
    const next = texto.slice(0, start) + token + texto.slice(end)
    setTexto(next)
    setSaved(false)
    // Restaurar foco y cursor después del token insertado
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + token.length
      el.setSelectionRange(pos, pos)
    })
  }

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
          Texto del mail. Usá los botones para insertar variables que se reemplazan
          con los datos de cada operación al generar las minutas.
          La configuración se guarda en la base de datos.
        </p>
      </div>

      {/* Botones de variables */}
      <div className="flex flex-wrap gap-1.5">
        {VARIABLES.map(({ label, token }) => (
          <button
            key={token}
            type="button"
            onClick={() => insertarVariable(token)}
            className="px-2 py-1 text-xs font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200 transition-colors"
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="h-64 bg-slate-100 rounded animate-pulse" />
      ) : (
        <Textarea
          ref={textareaRef}
          value={texto}
          onChange={(e) => { setTexto(e.target.value); setSaved(false) }}
          rows={18}
          className="font-mono text-sm resize-none"
          placeholder="Ingresá el texto de la plantilla estándar..."
        />
      )}

      <div className="flex items-center gap-3">
        <Button onClick={handleGuardar} disabled={guardar.isPending || !modificado}>
          {guardar.isPending ? 'Guardando...' : 'Guardar plantilla'}
        </Button>
        {saved && <span className="text-sm text-green-600">Guardado</span>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/PlantillaPage.tsx
git commit -m "feat(frontend): PlantillaPage — variable insertion buttons, update description text"
```

---

## Task 12: Frontend — ConfigDJPage.tsx con panel de reglas

**Files:**
- Modify: `frontend/src/pages/ConfigDJPage.tsx`

- [ ] **Step 1: Reescribir ConfigDJPage.tsx**

```tsx
// frontend/src/pages/ConfigDJPage.tsx
import { useState, useEffect, useRef } from 'react'
import { AlertTriangle, Plus, Trash2 } from 'lucide-react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { useConfigDJ, useGuardarConfigDJ } from '../hooks/useSession'
import type { ReglaDJ, CampoDJ, OperadorDJ, LogicaDJ } from '../types/domain'

const CAMPOS: { value: CampoDJ; label: string }[] = [
  { value: 'cantidad',    label: 'Cantidad' },
  { value: 'precio',      label: 'Precio' },
  { value: 'moneda',      label: 'Moneda' },
  { value: 'tipo',        label: 'Tipo operación' },
  { value: 'liquidacion', label: 'Liquidación' },
  { value: 'instrumento', label: 'Instrumento' },
]

const OPERADORES: { value: OperadorDJ; label: string }[] = [
  { value: '>',  label: 'mayor que (>)' },
  { value: '>=', label: 'mayor o igual (≥)' },
  { value: '<',  label: 'menor que (<)' },
  { value: '<=', label: 'menor o igual (≤)' },
  { value: '=',  label: 'igual (=)' },
  { value: '!=', label: 'distinto (≠)' },
]

const DJ_VARIABLES: { label: string; token: string }[] = [
  { label: 'Nombre cliente',  token: '{cliente_nombre}' },
  { label: 'Instrumento',     token: '{instrumento}' },
  { label: 'Cantidad',        token: '{cantidad}' },
  { label: 'Precio',          token: '{precio}' },
  { label: 'Moneda',          token: '{moneda}' },
  { label: 'Fecha operación', token: '{fecha_operacion}' },
]

const REGLA_VACIA: ReglaDJ = { campo: 'cantidad', operador: '>=', valor: '' }

export default function ConfigDJPage() {
  const { data, isLoading } = useConfigDJ()
  const guardar = useGuardarConfigDJ()
  const [activa, setActiva] = useState(false)
  const [incluirTexto, setIncluirTexto] = useState(false)
  const [textoAlerta, setTextoAlerta] = useState('')
  const [reglas, setReglas] = useState<ReglaDJ[]>([])
  const [logica, setLogica] = useState<LogicaDJ>('OR')
  const [saved, setSaved] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (data) {
      setActiva(data.activa)
      setIncluirTexto(data.incluir_texto_en_minuta)
      setTextoAlerta(data.texto_alerta)
      setReglas(data.reglas)
      setLogica(data.logica)
    }
  }, [data])

  function insertarVariable(token: string) {
    const el = textareaRef.current
    if (!el) return
    const start = el.selectionStart ?? textoAlerta.length
    const end = el.selectionEnd ?? textoAlerta.length
    const next = textoAlerta.slice(0, start) + token + textoAlerta.slice(end)
    setTextoAlerta(next)
    setSaved(false)
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + token.length
      el.setSelectionRange(pos, pos)
    })
  }

  function agregarRegla() {
    setReglas([...reglas, { ...REGLA_VACIA }])
    setSaved(false)
  }

  function eliminarRegla(idx: number) {
    setReglas(reglas.filter((_, i) => i !== idx))
    setSaved(false)
  }

  function actualizarRegla(idx: number, campo: keyof ReglaDJ, valor: string) {
    const nuevas = reglas.map((r, i) =>
      i === idx ? { ...r, [campo]: valor } : r
    )
    setReglas(nuevas as ReglaDJ[])
    setSaved(false)
  }

  const modificado = data
    ? activa !== data.activa
      || incluirTexto !== data.incluir_texto_en_minuta
      || textoAlerta !== data.texto_alerta
      || JSON.stringify(reglas) !== JSON.stringify(data.reglas)
      || logica !== data.logica
    : false

  async function handleGuardar() {
    try {
      await guardar.mutateAsync({
        activa,
        incluir_texto_en_minuta: incluirTexto,
        texto_alerta: textoAlerta,
        reglas,
        logica,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="h-10 bg-slate-100 rounded animate-pulse" />
        <div className="h-32 bg-slate-100 rounded animate-pulse" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Configuración DJ</h2>
        <p className="text-sm text-slate-500 mt-1">
          Configurá las condiciones que disparan el aviso de Declaración Jurada
          en las minutas generadas. La configuración se guarda en la base de datos.
        </p>
      </div>

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
          <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            activa ? 'translate-x-6' : 'translate-x-1'
          }`} />
        </button>
        <div>
          <p className="text-sm font-medium text-slate-800">
            {activa ? 'Detección de DJ activa' : 'Detección de DJ inactiva'}
          </p>
          <p className="text-xs text-slate-500">
            {activa
              ? 'El sistema evaluará las reglas para cada minuta generada'
              : 'No se detecta ni avisa sobre DJ en ninguna minuta'}
          </p>
        </div>
        {activa && <AlertTriangle className="h-4 w-4 text-amber-500 ml-auto shrink-0" />}
      </div>

      {activa && (
        <>
          {/* Panel de reglas */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">
                Reglas de activación
              </label>
              {reglas.length > 1 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Lógica entre reglas:</span>
                  {(['OR', 'AND'] as LogicaDJ[]).map((l) => (
                    <button
                      key={l}
                      type="button"
                      onClick={() => { setLogica(l); setSaved(false) }}
                      className={`px-2 py-0.5 text-xs font-mono rounded border transition-colors ${
                        logica === l
                          ? 'bg-slate-800 text-white border-slate-800'
                          : 'bg-white text-slate-600 border-slate-300 hover:border-slate-400'
                      }`}
                    >
                      {l}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {reglas.length === 0 && (
              <p className="text-xs text-slate-400 py-3 text-center border border-dashed border-slate-200 rounded-lg">
                Sin reglas — la DJ nunca se activará aunque esté habilitada.
                Agregá al menos una condición.
              </p>
            )}

            {reglas.map((regla, idx) => (
              <div key={idx} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <select
                  value={regla.campo}
                  onChange={(e) => actualizarRegla(idx, 'campo', e.target.value)}
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  {CAMPOS.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
                <select
                  value={regla.operador}
                  onChange={(e) => actualizarRegla(idx, 'operador', e.target.value)}
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  {OPERADORES.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={regla.valor}
                  onChange={(e) => actualizarRegla(idx, 'valor', e.target.value)}
                  placeholder="valor"
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400 w-32 font-mono"
                />
                <button
                  type="button"
                  onClick={() => eliminarRegla(idx)}
                  className="ml-auto text-slate-400 hover:text-red-500 transition-colors"
                  aria-label="Eliminar regla"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}

            <Button variant="outline" size="sm" onClick={agregarRegla} className="gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Agregar regla
            </Button>
          </div>

          {/* Toggle incluir texto en minuta */}
          <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
            <button
              type="button"
              role="switch"
              aria-checked={incluirTexto}
              onClick={() => { setIncluirTexto(!incluirTexto); setSaved(false) }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
                incluirTexto ? 'bg-slate-800' : 'bg-slate-200'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                incluirTexto ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {incluirTexto ? 'Incluir texto DJ en la minuta' : 'Solo mostrar aviso ⚠'}
              </p>
              <p className="text-xs text-slate-500">
                {incluirTexto
                  ? 'El texto de DJ configurado abajo se agrega al cuerpo de la minuta'
                  : 'La minuta muestra solo el ícono ⚠ — adjuntá el archivo DJ manualmente'}
              </p>
            </div>
          </div>

          {/* Texto de alerta DJ */}
          {incluirTexto && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                Texto de la Declaración Jurada
              </label>
              <div className="flex flex-wrap gap-1.5">
                {DJ_VARIABLES.map(({ label, token }) => (
                  <button
                    key={token}
                    type="button"
                    onClick={() => insertarVariable(token)}
                    className="px-2 py-1 text-xs font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
              <Textarea
                ref={textareaRef}
                value={textoAlerta}
                onChange={(e) => { setTextoAlerta(e.target.value); setSaved(false) }}
                rows={8}
                className="font-mono text-sm resize-none"
                placeholder="Ingresá el texto de la Declaración Jurada. Podés usar variables como {cliente_nombre}..."
              />
            </div>
          )}
        </>
      )}

      <div className="flex items-center gap-3">
        <Button onClick={handleGuardar} disabled={guardar.isPending || !modificado}>
          {guardar.isPending ? 'Guardando...' : 'Guardar configuración'}
        </Button>
        {saved && <span className="text-sm text-green-600">Guardado</span>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ConfigDJPage.tsx
git commit -m "feat(frontend): ConfigDJPage — rules panel, OR/AND selector, incluir_texto toggle, variable buttons"
```

---

## Task 13: Verificación final

- [ ] **Step 1: Correr todos los tests backend**

```bash
cd backend
python -m pytest tests/ -v
```

Resultado esperado: todos PASSED, sin warnings de importación.

- [ ] **Step 2: Verificar que el backend levanta sin errores**

```bash
uvicorn app.main:app --reload
```

Resultado esperado: servidor corriendo, sin errores de importación en consola.

- [ ] **Step 3: Verificar que el frontend compila sin errores de tipos**

```bash
cd frontend
npm run build
```

Resultado esperado: build exitoso sin errores TypeScript.

- [ ] **Step 4: Smoke test manual**

1. Login con `middleoffice` / `CambiarEstaPass123!` + TOTP
2. Ir a **Plantilla Estándar** → verificar que carga el texto del DB
3. Hacer clic en botón "Nombre cliente" → verifica que inserta `{cliente_nombre}` en el cursor
4. Editar y guardar → recargar la página → verificar que persiste
5. Ir a **Config DJ** → activar DJ
6. Agregar regla: `cantidad >= 1000000`
7. Cambiar lógica a AND, luego de vuelta a OR
8. Activar "Incluir texto DJ en la minuta" → verificar que aparece el textarea
9. Insertar variable `{cliente_nombre}` en el texto DJ
10. Guardar → recargar → verificar persistencia
11. Subir un Excel de prueba → verificar que las minutas se generan con la plantilla customizada

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "feat: ADR-0007 complete — persistent plantilla and config DJ with rule-based DJ detection"
```
