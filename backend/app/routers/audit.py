from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.audit import AuditEventResponse
from app.services.audit import get_events_for_orden, export_audit_trail_excel

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{orden_id}/export/excel")
def export_audit_excel(
    orden_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    content = export_audit_trail_excel(orden_id, db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=audit_{orden_id}.xlsx"
        },
    )


@router.get("/{orden_id}", response_model=list[AuditEventResponse])
def get_audit_trail(
    orden_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return get_events_for_orden(orden_id, db)
