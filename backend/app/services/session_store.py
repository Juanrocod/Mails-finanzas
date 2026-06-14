from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

DEFAULT_PLANTILLA = (
    "Estimado/a {cliente_nombre},\n\n"
    "Nos complace confirmar la operación realizada en el día de hoy.\n\n"
    "Quedamos a su disposición ante cualquier consulta.\n\n"
    "Saludos cordiales."
)


@dataclass
class MinutaSession:
    id: str
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
    dj_texto: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


@dataclass
class _ConfigDJ:
    activa: bool = False
    texto_alerta: str = ""


@dataclass
class _SessionData:
    minutas: list[MinutaSession] = field(default_factory=list)
    plantilla: str = field(default_factory=lambda: DEFAULT_PLANTILLA)
    config_dj: _ConfigDJ = field(default_factory=_ConfigDJ)


_store: dict[str, _SessionData] = {}


def _get_or_create(user_id: str) -> _SessionData:
    if user_id not in _store:
        _store[user_id] = _SessionData()
    return _store[user_id]


def get_session(user_id: str) -> _SessionData:
    return _get_or_create(user_id)


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)


def add_minutas(user_id: str, minutas: list[MinutaSession]) -> None:
    _get_or_create(user_id).minutas.extend(minutas)


def get_minutas(user_id: str, estado: str) -> list[MinutaSession]:
    return [m for m in _get_or_create(user_id).minutas if m.estado == estado]


def get_minuta(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    for m in _get_or_create(user_id).minutas:
        if m.id == minuta_id:
            return m
    return None


def update_minuta_texto(user_id: str, minuta_id: str, texto: str) -> Optional[MinutaSession]:
    m = get_minuta(user_id, minuta_id)
    if m is None:
        return None
    m.texto_minuta = texto
    m.texto_editado = True
    return m


def marcar_enviada(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    m = get_minuta(user_id, minuta_id)
    if m is None:
        return None
    m.estado = "ENVIADO"
    return m


def get_plantilla(user_id: str) -> str:
    return _get_or_create(user_id).plantilla


def set_plantilla(user_id: str, texto: str) -> None:
    _get_or_create(user_id).plantilla = texto


def get_config_dj(user_id: str) -> _ConfigDJ:
    return _get_or_create(user_id).config_dj


def set_config_dj(user_id: str, activa: bool, texto_alerta: str) -> None:
    _get_or_create(user_id).config_dj = _ConfigDJ(activa=activa, texto_alerta=texto_alerta)
