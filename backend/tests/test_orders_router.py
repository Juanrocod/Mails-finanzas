import pytest


def test_approve_orden(client, auth_headers, seeded_borrador_orden):
    r = client.post(f"/orders/{seeded_borrador_orden}/approve", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "APROBADO"


def test_edit_text_in_borrador(client, auth_headers, seeded_borrador_orden):
    r = client.patch(
        f"/orders/{seeded_borrador_orden}/text",
        json={"texto_minuta": "texto editado por test"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["texto_minuta"] == "texto editado por test"
    assert data["texto_editado"] is True


def test_edit_text_after_approval_rejected(client, auth_headers, seeded_borrador_orden):
    # Approve first
    client.post(f"/orders/{seeded_borrador_orden}/approve", headers=auth_headers)
    # Now try to edit — should be rejected
    r = client.patch(
        f"/orders/{seeded_borrador_orden}/text",
        json={"texto_minuta": "no se puede"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_approve_then_send(client, auth_headers, seeded_borrador_orden):
    client.post(f"/orders/{seeded_borrador_orden}/approve", headers=auth_headers)
    r = client.post(f"/orders/{seeded_borrador_orden}/send", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "ENVIADO"


def test_approve_send_confirm(client, auth_headers, seeded_borrador_orden):
    client.post(f"/orders/{seeded_borrador_orden}/approve", headers=auth_headers)
    client.post(f"/orders/{seeded_borrador_orden}/send", headers=auth_headers)
    r = client.post(f"/orders/{seeded_borrador_orden}/confirm", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "CONFIRMADO"


def test_approve_not_found(client, auth_headers):
    r = client.post(
        "/orders/00000000-0000-0000-0000-000000000000/approve",
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_send_not_found(client, auth_headers):
    r = client.post(
        "/orders/00000000-0000-0000-0000-000000000000/send",
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_check_alerts_endpoint(client, auth_headers):
    r = client.post("/orders/admin/check-alerts", headers=auth_headers)
    assert r.status_code == 200
    assert "alertas_generadas" in r.json()


def test_requires_auth(client, seeded_borrador_orden):
    r = client.post(f"/orders/{seeded_borrador_orden}/approve")
    assert r.status_code == 403
