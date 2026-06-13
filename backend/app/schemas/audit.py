from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    orden_id: UUID
    usuario_id: Optional[UUID]
    accion: str
    ip_origen: Optional[str]
    timestamp: datetime
    detalle: Optional[Any]
