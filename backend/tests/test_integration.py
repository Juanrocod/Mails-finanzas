"""
End-to-end integration test: upload → edit → approve → send → confirm
Verifies that all state transitions work together and the audit trail
records every action.
"""

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_full_order_flow(client, auth_headers, make_valid_excel):
    # 1. Upload Excel — creates BORRADOR
    r = client.post(
        "/uploads/excel",
        files={"file": ("operaciones.xlsx", make_valid_excel, XLSX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    assert r.status_code == 201, f"Upload failed: {r.text}"
    upload_data = r.json()
    assert upload_data["ordenes_validas"] == 1
    assert upload_data["ordenes_con_error"] == 0

    # 2. Check it appears in borradores
    r = client.get("/dashboard/borradores", headers=auth_headers)
    assert r.status_code == 200
    borradores = r.json()
    assert borradores["total"] >= 1
    orden_id = borradores["items"][0]["id"]

    # 3. Edit the minuta text
    r = client.patch(
        f"/orders/{orden_id}/text",
        json={"texto_minuta": "Texto corregido por Middle Office"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["texto_editado"] is True
    assert r.json()["texto_minuta"] == "Texto corregido por Middle Office"

    # 4. Approve
    r = client.post(f"/orders/{orden_id}/approve", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "APROBADO"

    # 5. Verify it moved out of borradores
    r = client.get("/dashboard/borradores", headers=auth_headers)
    borrador_ids = [o["id"] for o in r.json()["items"]]
    assert orden_id not in borrador_ids

    # 6. Verify it appears in aprobados
    r = client.get("/dashboard/aprobados", headers=auth_headers)
    aprobado_ids = [o["id"] for o in r.json()["items"]]
    assert orden_id in aprobado_ids

    # 7. Send
    r = client.post(f"/orders/{orden_id}/send", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "ENVIADO"

    # 8. Confirm
    r = client.post(f"/orders/{orden_id}/confirm", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "CONFIRMADO"

    # 9. Verify it appears in confirmados
    r = client.get("/dashboard/confirmados", headers=auth_headers)
    confirmado_ids = [o["id"] for o in r.json()["items"]]
    assert orden_id in confirmado_ids

    # 10. Verify full audit trail
    r = client.get(f"/audit/{orden_id}", headers=auth_headers)
    assert r.status_code == 200
    events = r.json()
    acciones = [e["accion"] for e in events]
    assert "CREADA" in acciones
    assert "EDITADA" in acciones
    assert "APROBADA" in acciones
    assert "ENVIADA" in acciones
    assert "CONFIRMADA" in acciones

    # 11. Export audit trail as Excel
    r = client.get(f"/audit/{orden_id}/export/excel", headers=auth_headers)
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    assert len(r.content) > 100
