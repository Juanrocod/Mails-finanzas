import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AccionAudit(str, enum.Enum):
    CREADA = "CREADA"
    EDITADA = "EDITADA"
    APROBADA = "APROBADA"
    ENVIADA = "ENVIADA"
    CONFIRMADA = "CONFIRMADA"
    ALERTA_GENERADA = "ALERTA_GENERADA"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orden_id = Column(UUID(as_uuid=True), ForeignKey("ordenes.id"), nullable=False, index=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # None = system action
    accion = Column(Enum(AccionAudit), nullable=False)
    ip_origen = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    detalle = Column(JSON, nullable=True)


class DJTemplate(Base):
    __tablename__ = "dj_templates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), unique=True, nullable=False)
    texto = Column(Text, nullable=False)
    # reglas examples: {"instrumento": "AL30"} or {"monto_minimo": 100000} or {"tipo": "COMPRA", "moneda": "USD"}
    reglas = Column(JSON, nullable=False)
    prioridad = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
