from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, AccionAudit
from app.models.order import Orden, EstadoMinuta

VALID_TRANSITIONS: dict[EstadoMinuta, set[EstadoMinuta]] = {
    EstadoMinuta.BORRADOR: {EstadoMinuta.APROBADO},
    EstadoMinuta.APROBADO: {EstadoMinuta.ENVIADO},
    EstadoMinuta.ENVIADO: {EstadoMinuta.CONFIRMADO, EstadoMinuta.ALERTA},
    EstadoMinuta.ALERTA: {EstadoMinuta.CONFIRMADO},
    EstadoMinuta.CONFIRMADO: set(),
}

TRANSITION_TO_ACCION: dict[EstadoMinuta, AccionAudit] = {
    EstadoMinuta.APROBADO: AccionAudit.APROBADA,
    EstadoMinuta.ENVIADO: AccionAudit.ENVIADA,
    EstadoMinuta.CONFIRMADO: AccionAudit.CONFIRMADA,
    EstadoMinuta.ALERTA: AccionAudit.ALERTA_GENERADA,
}

ALERTA_THRESHOLD_HOURS = 24


def transition_state(
    orden: Orden,
    new_state: EstadoMinuta,
    usuario_id: Optional[UUID],
    ip_origen: Optional[str],
    db: Session,
) -> Orden:
    allowed = VALID_TRANSITIONS.get(orden.estado, set())
    if new_state not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Transición inválida: {orden.estado} → {new_state}",
        )
    orden.estado = new_state
    accion = TRANSITION_TO_ACCION[new_state]
    db.add(AuditEvent(
        orden_id=orden.id,
        usuario_id=usuario_id,
        accion=accion,
        ip_origen=ip_origen,
    ))
    db.flush()
    return orden


def edit_minuta_text(
    orden: Orden,
    nuevo_texto: str,
    usuario_id: Optional[UUID],
    ip_origen: Optional[str],
    db: Session,
) -> Orden:
    if orden.estado != EstadoMinuta.BORRADOR:
        raise HTTPException(
            status_code=400,
            detail="Solo se puede editar el texto de una Minuta en estado BORRADOR",
        )
    orden.texto_minuta = nuevo_texto
    orden.texto_editado = True
    db.add(AuditEvent(
        orden_id=orden.id,
        usuario_id=usuario_id,
        accion=AccionAudit.EDITADA,
        ip_origen=ip_origen,
    ))
    db.flush()
    return orden


def get_orders_by_estado(
    estado: EstadoMinuta,
    db: Session,
    page: int = 1,
    size: int = 50,
) -> dict:
    query = db.query(Orden).filter(Orden.estado == estado)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"items": items, "total": total, "page": page, "size": size}


def mark_overdue_as_alerta(db: Session) -> int:
    threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=ALERTA_THRESHOLD_HOURS)
    overdue = (
        db.query(Orden)
        .filter(Orden.estado == EstadoMinuta.ENVIADO, Orden.updated_at < threshold)
        .all()
    )
    for orden in overdue:
        orden.estado = EstadoMinuta.ALERTA
        db.add(AuditEvent(
            orden_id=orden.id,
            usuario_id=None,
            accion=AccionAudit.ALERTA_GENERADA,
            ip_origen=None,
        ))
    db.flush()
    return len(overdue)
