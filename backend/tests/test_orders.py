import pytest
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from app.models.order import Orden, ExcelUpload, EstadoMinuta, TipoOperacion, CondicionLiquidacion
from app.models.user import User
from app.models.audit import AuditEvent, AccionAudit
from app.core.security import hash_password
from app import services


def make_user(db):
    user = User(
        username=f"u_{uuid4().hex[:8]}",
        hashed_password=hash_password("pass"),
        totp_secret="JBSWY3DPEHPK3PXP",
    )
    db.add(user)
    db.flush()
    return user


def make_upload(db, user):
    upload = ExcelUpload(
        usuario_id=user.id,
        nombre_archivo="test.xlsx",
        total_ordenes=1,
        ordenes_validas=1,
        ordenes_con_error=0,
    )
    db.add(upload)
    db.flush()
    return upload


def make_orden(db, estado=EstadoMinuta.BORRADOR):
    user = make_user(db)
    upload = make_upload(db, user)
    orden = Orden(
        excel_upload_id=upload.id,
        cliente_nombre="Test Cliente",
        cliente_email="cliente@test.com",
        cuenta_comitente="111",
        cuenta_cotapartista="222",
        instrumento="AL30",
        tipo=TipoOperacion.COMPRA,
        cantidad=100,
        precio=70.0,
        moneda="USD",
        liquidacion=CondicionLiquidacion.HS24,
        fecha_operacion=datetime(2026, 6, 13, 10, 0),
        estado=estado,
        texto_minuta="Texto de prueba",
        texto_editado=False,
    )
    db.add(orden)
    db.flush()
    return orden, user


# --- transition_state tests ---

def test_borrador_to_aprobado(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db)
    result = transition_state(orden, EstadoMinuta.APROBADO, user.id, "127.0.0.1", db)
    assert result.estado == EstadoMinuta.APROBADO


def test_aprobado_to_enviado(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db, EstadoMinuta.APROBADO)
    result = transition_state(orden, EstadoMinuta.ENVIADO, user.id, "127.0.0.1", db)
    assert result.estado == EstadoMinuta.ENVIADO


def test_enviado_to_confirmado(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db, EstadoMinuta.ENVIADO)
    result = transition_state(orden, EstadoMinuta.CONFIRMADO, user.id, "127.0.0.1", db)
    assert result.estado == EstadoMinuta.CONFIRMADO


def test_enviado_to_alerta(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db, EstadoMinuta.ENVIADO)
    result = transition_state(orden, EstadoMinuta.ALERTA, None, "system", db)
    assert result.estado == EstadoMinuta.ALERTA


def test_alerta_to_confirmado(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db, EstadoMinuta.ALERTA)
    result = transition_state(orden, EstadoMinuta.CONFIRMADO, user.id, "127.0.0.1", db)
    assert result.estado == EstadoMinuta.CONFIRMADO


def test_invalid_transition_borrador_to_enviado(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db)
    with pytest.raises(HTTPException) as exc_info:
        transition_state(orden, EstadoMinuta.ENVIADO, user.id, "127.0.0.1", db)
    assert exc_info.value.status_code == 400


def test_invalid_transition_aprobado_to_borrador(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db, EstadoMinuta.APROBADO)
    with pytest.raises(HTTPException) as exc_info:
        transition_state(orden, EstadoMinuta.BORRADOR, user.id, "127.0.0.1", db)
    assert exc_info.value.status_code == 400


def test_invalid_transition_confirmado_to_anything(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db, EstadoMinuta.CONFIRMADO)
    with pytest.raises(HTTPException) as exc_info:
        transition_state(orden, EstadoMinuta.ENVIADO, user.id, "127.0.0.1", db)
    assert exc_info.value.status_code == 400


def test_transition_creates_audit_event(db):
    from app.services.orders import transition_state
    orden, user = make_orden(db)
    transition_state(orden, EstadoMinuta.APROBADO, user.id, "127.0.0.1", db)
    events = db.query(AuditEvent).filter(AuditEvent.orden_id == orden.id).all()
    assert len(events) == 1
    assert events[0].accion == AccionAudit.APROBADA


# --- edit_minuta_text tests ---

def test_edit_text_in_borrador(db):
    from app.services.orders import edit_minuta_text
    orden, user = make_orden(db)
    result = edit_minuta_text(orden, "texto nuevo", user.id, "127.0.0.1", db)
    assert result.texto_minuta == "texto nuevo"
    assert result.texto_editado is True


def test_edit_creates_audit_event(db):
    from app.services.orders import edit_minuta_text
    orden, user = make_orden(db)
    edit_minuta_text(orden, "nuevo", user.id, "127.0.0.1", db)
    events = db.query(AuditEvent).filter(AuditEvent.orden_id == orden.id).all()
    assert len(events) == 1
    assert events[0].accion == AccionAudit.EDITADA


def test_edit_text_after_approval_raises(db):
    from app.services.orders import edit_minuta_text
    orden, user = make_orden(db, EstadoMinuta.APROBADO)
    with pytest.raises(HTTPException) as exc_info:
        edit_minuta_text(orden, "x", user.id, "127.0.0.1", db)
    assert exc_info.value.status_code == 400


# --- get_orders_by_estado tests ---

def test_get_orders_by_estado_returns_matching(db):
    from app.services.orders import get_orders_by_estado
    orden, _ = make_orden(db, EstadoMinuta.BORRADOR)
    make_orden(db, EstadoMinuta.APROBADO)
    result = get_orders_by_estado(EstadoMinuta.BORRADOR, db)
    estados = [o.estado for o in result["items"]]
    assert all(e == EstadoMinuta.BORRADOR for e in estados)
    assert result["total"] >= 1


def test_get_orders_by_estado_pagination(db):
    from app.services.orders import get_orders_by_estado
    for _ in range(5):
        make_orden(db, EstadoMinuta.BORRADOR)
    result = get_orders_by_estado(EstadoMinuta.BORRADOR, db, page=1, size=2)
    assert len(result["items"]) == 2
    assert result["size"] == 2


# --- mark_overdue_as_alerta tests ---

def test_mark_overdue_as_alerta(db):
    from app.services.orders import mark_overdue_as_alerta
    from datetime import timedelta
    from sqlalchemy import update
    from app.models.order import Orden as OrdenModel

    orden, _ = make_orden(db, EstadoMinuta.ENVIADO)
    # Manually set updated_at to 25 hours ago to simulate overdue
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)
    db.execute(
        update(OrdenModel).where(OrdenModel.id == orden.id).values(updated_at=old_time)
    )
    db.flush()

    count = mark_overdue_as_alerta(db)
    assert count >= 1
    db.refresh(orden)
    assert orden.estado == EstadoMinuta.ALERTA
