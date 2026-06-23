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


# --- Multi-DJ CRUD tests ---


def test_load_all_config_dj_empty(db):
    result = db_config.load_all_config_dj(db)
    assert result == []


def test_create_config_dj(db):
    data = ConfigDJData(
        nombre="DJ por monto",
        activa=True,
        incluir_texto_en_minuta=True,
        texto_alerta="Alerta: monto alto",
        reglas=[{"campo": "monto", "operador": ">=", "valor": "1000000"}],
        logica="AND",
    )
    created = db_config.create_config_dj(db, data)
    assert created.id is not None
    assert created.nombre == "DJ por monto"
    assert created.activa is True


def test_create_multiple_djs(db):
    db_config.create_config_dj(db, ConfigDJData(nombre="DJ 1"))
    db_config.create_config_dj(db, ConfigDJData(nombre="DJ 2"))
    all_djs = db_config.load_all_config_dj(db)
    assert len(all_djs) == 2
    assert all_djs[0].nombre == "DJ 1"
    assert all_djs[1].nombre == "DJ 2"


def test_update_config_dj(db):
    created = db_config.create_config_dj(db, ConfigDJData(nombre="Original"))
    updated = db_config.update_config_dj(db, created.id, ConfigDJData(nombre="Editada", activa=True))
    assert updated is not None
    assert updated.nombre == "Editada"
    assert updated.activa is True


def test_update_config_dj_nonexistent_returns_none(db):
    result = db_config.update_config_dj(db, 9999, ConfigDJData(nombre="x"))
    assert result is None


def test_delete_config_dj(db):
    created = db_config.create_config_dj(db, ConfigDJData(nombre="Para borrar"))
    assert db_config.delete_config_dj(db, created.id) is True
    assert db_config.load_all_config_dj(db) == []


def test_delete_config_dj_nonexistent_returns_false(db):
    assert db_config.delete_config_dj(db, 9999) is False


