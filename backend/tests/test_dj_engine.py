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
