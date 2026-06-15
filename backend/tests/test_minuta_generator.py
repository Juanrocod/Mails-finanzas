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
