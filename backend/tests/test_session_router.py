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
