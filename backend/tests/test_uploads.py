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
