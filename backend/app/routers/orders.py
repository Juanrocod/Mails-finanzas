from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.order import Orden, EstadoMinuta
from app.models.user import User
from app.schemas.order import OrdenResponse, EditTextRequest
from app.services.orders import (
    transition_state,
    edit_minuta_text,
    mark_overdue_as_alerta,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _get_orden_or_404(orden_id: UUID, db: Session) -> Orden:
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden


# NOTE: /admin/check-alerts must be defined BEFORE /{orden_id} routes
# to prevent FastAPI from matching "admin" as a UUID.
@router.post("/admin/check-alerts")
def check_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = mark_overdue_as_alerta(db)
    db.commit()
    return {"alertas_generadas": count}


@router.patch("/{orden_id}/text", response_model=OrdenResponse)
def edit_text(
    orden_id: UUID,
    body: EditTextRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orden = _get_orden_or_404(orden_id, db)
    ip = request.client.host if request.client else "unknown"
    result = edit_minuta_text(orden, body.texto_minuta, current_user.id, ip, db)
    db.commit()
    return result


@router.post("/{orden_id}/approve", response_model=OrdenResponse)
def approve(
    orden_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orden = _get_orden_or_404(orden_id, db)
    ip = request.client.host if request.client else "unknown"
    result = transition_state(orden, EstadoMinuta.APROBADO, current_user.id, ip, db)
    db.commit()
    return result


@router.post("/{orden_id}/send", response_model=OrdenResponse)
def send(
    orden_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orden = _get_orden_or_404(orden_id, db)
    ip = request.client.host if request.client else "unknown"
    result = transition_state(orden, EstadoMinuta.ENVIADO, current_user.id, ip, db)
    db.commit()
    return result


@router.post("/{orden_id}/confirm", response_model=OrdenResponse)
def confirm(
    orden_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orden = _get_orden_or_404(orden_id, db)
    ip = request.client.host if request.client else "unknown"
    result = transition_state(orden, EstadoMinuta.CONFIRMADO, current_user.id, ip, db)
    db.commit()
    return result
