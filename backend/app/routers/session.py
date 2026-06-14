# backend/app/routers/session.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.session import (
    SessionMinutasResponse,
    MinutaSchema,
    EditTextoRequest,
    PlantillaSchema,
    ConfigDJSchema,
)
from app.services import session_store

router = APIRouter(tags=["session"])


@router.get("/session/minutas", response_model=SessionMinutasResponse)
def get_session_minutas(
    estado: str = "BORRADOR",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)
    minutas = session_store.get_minutas(user_id, estado)
    items = [MinutaSchema(**m.__dict__) for m in minutas]
    return SessionMinutasResponse(items=items, total=len(items))


@router.patch("/session/minutas/{minuta_id}/texto", response_model=MinutaSchema)
def patch_minuta_texto(
    minuta_id: str,
    body: EditTextoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.update_minuta_texto(str(current_user.id), minuta_id, body.texto_minuta)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.patch("/session/minutas/{minuta_id}/enviado", response_model=MinutaSchema)
def patch_minuta_enviado(
    minuta_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = session_store.marcar_enviada(str(current_user.id), minuta_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Minuta no encontrada")
    return MinutaSchema(**updated.__dict__)


@router.get("/plantilla", response_model=PlantillaSchema)
def get_plantilla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    texto = session_store.get_plantilla(str(current_user.id))
    return PlantillaSchema(texto=texto)


@router.patch("/plantilla", response_model=PlantillaSchema)
def patch_plantilla(
    body: PlantillaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_store.set_plantilla(str(current_user.id), body.texto)
    return body


@router.get("/config/dj", response_model=ConfigDJSchema)
def get_config_dj(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = session_store.get_config_dj(str(current_user.id))
    return ConfigDJSchema(activa=cfg.activa, texto_alerta=cfg.texto_alerta)


@router.patch("/config/dj", response_model=ConfigDJSchema)
def patch_config_dj(
    body: ConfigDJSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_store.set_config_dj(str(current_user.id), body.activa, body.texto_alerta)
    return body
