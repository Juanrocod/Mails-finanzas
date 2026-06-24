from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional


SESSION_TTL = timedelta(hours=12)


@dataclass
class MinutaSession:
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
    estado_orden: str          # Estado de la orden en la plataforma (ej: "Ejecutada")
    cantidad_operada: float
    precio_operado: float
    operador: str
    origen: str
    asesor: str
    requiere_conformidad: int
    # Campos de sesión
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: Literal["BORRADOR", "ENVIADO", "FILTRADA"]
    filtro_motivo: Optional[str]
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


@dataclass
class _SessionData:
    minutas: list[MinutaSession] = field(default_factory=list)
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_store: dict[str, _SessionData] = {}


def _get_or_create(user_id: str) -> _SessionData:
    session = _store.get(user_id)
    if session is not None and datetime.now(timezone.utc) - session.last_accessed > SESSION_TTL:
        del _store[user_id]
        session = None
    if session is None:
        session = _SessionData()
        _store[user_id] = session
    session.last_accessed = datetime.now(timezone.utc)
    return session


def clear_session(user_id: str) -> None:
    _store.pop(user_id, None)


def clear_borradores_y_filtradas(user_id: str) -> None:
    """Limpia todas las minutas al subir un nuevo Excel."""
    session = _get_or_create(user_id)
    session.minutas = []


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
    if m is None or m.estado != "BORRADOR":
        return None
    m.estado = "ENVIADO"
    return m


def agregar_filtrada_a_borrador(user_id: str, minuta_id: str) -> Optional[MinutaSession]:
    """Mueve una Minuta de FILTRADA a BORRADOR."""
    m = get_minuta(user_id, minuta_id)
    if m is None or m.estado != "FILTRADA":
        return None
    m.estado = "BORRADOR"
    return m


def agregar_todas_filtradas_a_borrador(user_id: str) -> int:
    """Mueve todas las Minutas FILTRADAS a BORRADOR. Retorna la cantidad movida."""
    session = _get_or_create(user_id)
    count = 0
    for m in session.minutas:
        if m.estado == "FILTRADA":
            m.estado = "BORRADOR"
            count += 1
    return count
