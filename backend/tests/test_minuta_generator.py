from app.services.minuta_generator import generate_minuta_text, _fmt_num
from datetime import datetime


DATOS_BASE = {
    "cliente_nombre": "KIRIADRE OMAR",
    "cuenta_comitente": "70164",
    "cuenta_cotapartista": "177",
    "id_orden": 100453202,
    "fecha_operacion": datetime(2026, 6, 16, 11, 12, 18),
    "fecha_liquidacion": "16/06/2026",
    "operacion": "Compra CI",
    "instrumento": "AL30",
    "moneda": "Pesos",
    "cantidad": 350.0,
    "precio": 936.6,
    "monto": 327810.0,
    "estado": "Ejecutada",
    "cantidad_operada": 350.0,
    "precio_operado": 936.6,
    "operador": "kobruna425582",
    "origen": "Cliente",
    "asesor": "Wenceslao Jakob",
    "requiere_conformidad": 0,
}


def test_generate_basic_minuta():
    plantilla = "Cliente: {cliente_nombre}\nOperación: {operacion}\nMonto: {monto}"
    texto = generate_minuta_text(plantilla, DATOS_BASE)
    assert "KIRIADRE OMAR" in texto
    assert "Compra CI" in texto
    assert "327.810" in texto  # formato es-AR


def test_negative_one_renders_na():
    plantilla = "Cantidad: {cantidad}\nPrecio: {precio}"
    datos = {**DATOS_BASE, "cantidad": -1.0, "precio": -1.0}
    texto = generate_minuta_text(plantilla, datos)
    assert texto == "Cantidad: N/A\nPrecio: N/A"


def test_unknown_variable_left_as_literal():
    plantilla = "Hola {variable_inexistente}"
    texto = generate_minuta_text(plantilla, DATOS_BASE)
    assert "{variable_inexistente}" in texto


def test_dj_texto_appended():
    plantilla = "Cliente: {cliente_nombre}"
    texto = generate_minuta_text(plantilla, DATOS_BASE, dj_texto="Texto DJ aquí")
    assert "DECLARACIÓN JURADA" in texto
    assert "Texto DJ aquí" in texto


def test_fmt_num_negative_one():
    assert _fmt_num(-1.0) == "N/A"


def test_fmt_num_integer():
    assert _fmt_num(1000.0) == "1.000"


def test_fmt_num_decimal():
    assert _fmt_num(936.6) == "936,60"
