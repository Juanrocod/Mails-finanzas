from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import datetime

_CAMPOS_PERMITIDOS = {
    "operacion", "operador", "origen", "estado", "moneda", "instrumento",
    "cantidad", "precio", "monto", "cantidad_operada", "precio_operado", "requiere_conformidad"
}
_OPERADORES_PERMITIDOS = {">", "<", "=", "!=", ">=", "<="}


class MinutaSchema(BaseModel):
    id: str
    # Campos del Excel
    cliente_nombre: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    id_orden: int
    fecha_operacion: datetime
    fecha_liquidacion: str
    operacion: str
    instrumento: str
    moneda: str
    cantidad: float
    precio: float
    monto: float
    estado_orden: str
    cantidad_operada: float
    precio_operado: float
    operador: str
    origen: str
    asesor: str
    requiere_conformidad: int
    # Campos de sesión
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


class SessionMinutasResponse(BaseModel):
    items: List[MinutaSchema]
    total: int


class RowErrorSchema(BaseModel):
    fila: int
    mensaje: str


class UploadMVPResponse(BaseModel):
    nombre_archivo: str
    total_ordenes: int
    ordenes_validas: int
    ordenes_con_error: int
    ordenes_filtradas: int
    errors: List[RowErrorSchema]
    minutas: List[MinutaSchema]


class EditTextoRequest(BaseModel):
    texto_minuta: str


class PlantillaSchema(BaseModel):
    texto: str


class ReglaSchema(BaseModel):
    campo: str
    operador: str
    valor: str

    @field_validator("campo")
    @classmethod
    def campo_valido(cls, v: str) -> str:
        if v not in _CAMPOS_PERMITIDOS:
            raise ValueError(f"campo '{v}' no permitido. Opciones: {sorted(_CAMPOS_PERMITIDOS)}")
        return v

    @field_validator("operador")
    @classmethod
    def operador_valido(cls, v: str) -> str:
        if v not in _OPERADORES_PERMITIDOS:
            raise ValueError(f"operador '{v}' no permitido. Opciones: {sorted(_OPERADORES_PERMITIDOS)}")
        return v


class ConfigDJSchema(BaseModel):
    activa: bool
    incluir_texto_en_minuta: bool = False
    texto_alerta: str
    reglas: List[ReglaSchema] = []
    logica: Literal["OR", "AND"] = "OR"
    activar_si_requiere_conformidad: bool = True


class ConfigFiltrosSchema(BaseModel):
    reglas: List[ReglaSchema] = []
    logica: Literal["OR", "AND"] = "OR"
