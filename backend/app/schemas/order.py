from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class OrdenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    excel_upload_id: UUID
    cliente_nombre: str
    cliente_email: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    instrumento: str
    tipo: str
    cantidad: float
    precio: float
    moneda: str
    liquidacion: str
    fecha_operacion: datetime
    dj_aplicada: bool
    dj_tipo: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    created_at: datetime
    updated_at: datetime


class EditTextRequest(BaseModel):
    texto_minuta: str


class RowErrorSchema(BaseModel):
    fila: int
    mensaje: str


class UploadResponse(BaseModel):
    upload_id: str
    nombre_archivo: str
    total_ordenes: int
    ordenes_validas: int
    ordenes_con_error: int
    errors: List[RowErrorSchema]


class DashboardPage(BaseModel):
    items: List[OrdenResponse]
    total: int
    page: int
    size: int
