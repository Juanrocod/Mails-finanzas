# backend/tests/test_session_store.py
import pytest
from datetime import datetime, timezone
from app.services.session_store import (
    clear_session,
    add_minutas,
    get_minutas,
    get_minuta,
    update_minuta_texto,
    marcar_enviada,
    agregar_filtrada_a_borrador,
    agregar_todas_filtradas_a_borrador,
    clear_borradores_y_filtradas,
    MinutaSession,
)


def _make_minuta(**overrides) -> MinutaSession:
    defaults = dict(
        id="test-id-1",
        cliente_nombre="Test Cliente",
        cuenta_comitente="12345",
        cuenta_cotapartista="",
        id_orden=999001,
        fecha_operacion=datetime(2026, 6, 16, 9, 0, 0),
        fecha_liquidacion="16/06/2026",
        operacion="Compra CI",
        instrumento="AL30",
        moneda="Pesos",
        cantidad=100.0,
        precio=500.0,
        monto=50000.0,
        estado_orden="Ejecutada",
        cantidad_operada=100.0,
        precio_operado=500.0,
        operador="testuser",
        origen="Cliente",
        asesor="Test Asesor",
        requiere_conformidad=0,
        dj_aplicada=False,
        dj_texto=None,
        estado="BORRADOR",
        filtro_motivo=None,
        texto_minuta="Texto de prueba",
        texto_editado=False,
        creado_en=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return MinutaSession(**defaults)


USER = "user-abc"


@pytest.fixture(autouse=True)
def limpia_store():
    clear_session(USER)
    yield
    clear_session(USER)


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

def test_get_session_returns_empty_by_default():
    assert get_minutas(USER, "BORRADOR") == []


def test_add_minutas_stores_them():
    m = _make_minuta()
    add_minutas(USER, [m])
    result = get_minutas(USER, "BORRADOR")
    assert len(result) == 1
    assert result[0].id == "test-id-1"


def test_get_minutas_filters_by_estado():
    m_borrador = _make_minuta(id="b1", estado="BORRADOR")
    m_enviado = _make_minuta(id="e1", estado="ENVIADO")
    add_minutas(USER, [m_borrador, m_enviado])
    assert [m.id for m in get_minutas(USER, "BORRADOR")] == ["b1"]
    assert [m.id for m in get_minutas(USER, "ENVIADO")] == ["e1"]


def test_get_minutas_filtradas():
    m_filtrada = _make_minuta(id="f1", estado="FILTRADA")
    m_borrador = _make_minuta(id="b1", estado="BORRADOR")
    add_minutas(USER, [m_filtrada, m_borrador])
    filtradas = get_minutas(USER, "FILTRADA")
    assert [m.id for m in filtradas] == ["f1"]


def test_get_minuta_by_id():
    m = _make_minuta(id="x99")
    add_minutas(USER, [m])
    found = get_minuta(USER, "x99")
    assert found is not None
    assert found.id == "x99"


def test_get_minuta_unknown_id_returns_none():
    assert get_minuta(USER, "no-existe") is None


# ---------------------------------------------------------------------------
# update_minuta_texto
# ---------------------------------------------------------------------------

def test_update_minuta_texto():
    m = _make_minuta(id="u1")
    add_minutas(USER, [m])
    updated = update_minuta_texto(USER, "u1", "nuevo texto")
    assert updated is not None
    assert updated.texto_minuta == "nuevo texto"
    assert updated.texto_editado is True


def test_update_minuta_texto_unknown_returns_none():
    assert update_minuta_texto(USER, "nope", "x") is None


# ---------------------------------------------------------------------------
# marcar_enviada
# ---------------------------------------------------------------------------

def test_marcar_enviada_changes_estado():
    m = _make_minuta(id="v1")
    add_minutas(USER, [m])
    updated = marcar_enviada(USER, "v1")
    assert updated is not None
    assert updated.estado == "ENVIADO"


def test_marcar_enviada_unknown_returns_none():
    assert marcar_enviada(USER, "nope") is None


def test_marcar_enviada_filtrada_returns_none():
    """Only BORRADOR can be marked as sent."""
    m = _make_minuta(id="f1", estado="FILTRADA")
    add_minutas(USER, [m])
    result = marcar_enviada(USER, "f1")
    assert result is None


# ---------------------------------------------------------------------------
# agregar_filtrada_a_borrador
# ---------------------------------------------------------------------------

def test_agregar_filtrada_a_borrador_moves_to_borrador():
    m = _make_minuta(id="fi1", estado="FILTRADA")
    add_minutas(USER, [m])
    result = agregar_filtrada_a_borrador(USER, "fi1")
    assert result is not None
    assert result.estado == "BORRADOR"
    # Verify it now appears in BORRADOR list
    borradores = get_minutas(USER, "BORRADOR")
    assert any(b.id == "fi1" for b in borradores)
    # And no longer in FILTRADA
    filtradas = get_minutas(USER, "FILTRADA")
    assert not any(f.id == "fi1" for f in filtradas)


def test_agregar_filtrada_unknown_returns_none():
    assert agregar_filtrada_a_borrador(USER, "no-existe") is None


def test_agregar_filtrada_borrador_not_movable():
    """A BORRADOR minuta cannot be added via agregar_filtrada_a_borrador."""
    m = _make_minuta(id="b1", estado="BORRADOR")
    add_minutas(USER, [m])
    result = agregar_filtrada_a_borrador(USER, "b1")
    assert result is None


# ---------------------------------------------------------------------------
# agregar_todas_filtradas_a_borrador
# ---------------------------------------------------------------------------

def test_agregar_todas_filtradas_moves_all():
    m1 = _make_minuta(id="f1", estado="FILTRADA")
    m2 = _make_minuta(id="f2", estado="FILTRADA")
    m3 = _make_minuta(id="b1", estado="BORRADOR")
    add_minutas(USER, [m1, m2, m3])
    count = agregar_todas_filtradas_a_borrador(USER)
    assert count == 2
    assert get_minutas(USER, "FILTRADA") == []
    borradores = get_minutas(USER, "BORRADOR")
    assert len(borradores) == 3


def test_agregar_todas_filtradas_empty_returns_zero():
    m = _make_minuta(id="b1", estado="BORRADOR")
    add_minutas(USER, [m])
    count = agregar_todas_filtradas_a_borrador(USER)
    assert count == 0


# ---------------------------------------------------------------------------
# clear_borradores_y_filtradas
# ---------------------------------------------------------------------------

def test_clear_borradores_y_filtradas_clears_all():
    m_b = _make_minuta(id="b1", estado="BORRADOR")
    m_f = _make_minuta(id="f1", estado="FILTRADA")
    m_e = _make_minuta(id="e1", estado="ENVIADO")
    add_minutas(USER, [m_b, m_f, m_e])
    clear_borradores_y_filtradas(USER)
    assert get_minutas(USER, "BORRADOR") == []
    assert get_minutas(USER, "FILTRADA") == []
    assert get_minutas(USER, "ENVIADO") == []


# ---------------------------------------------------------------------------
# clear_session
# ---------------------------------------------------------------------------

def test_clear_session_resets_minutas():
    m = _make_minuta()
    add_minutas(USER, [m])
    clear_session(USER)
    assert get_minutas(USER, "BORRADOR") == []
