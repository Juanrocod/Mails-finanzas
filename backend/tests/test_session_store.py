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
