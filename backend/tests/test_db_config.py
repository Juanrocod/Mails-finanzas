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
