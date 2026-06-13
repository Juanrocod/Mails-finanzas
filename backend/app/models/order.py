import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Enum, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from app.core.security import EncryptedString


class TipoOperacion(str, enum.Enum):
    COMPRA = "COMPRA"
    VENTA = "VENTA"


class CondicionLiquidacion(str, enum.Enum):
    CI = "CI"
    HS24 = "24HS"
    HS48 = "48HS"


class EstadoMinuta(str, enum.Enum):
    BORRADOR = "BORRADOR"
    APROBADO = "APROBADO"
    ENVIADO = "ENVIADO"
    CONFIRMADO = "CONFIRMADO"
    ALERTA = "ALERTA"


class ExcelUpload(Base):
    __tablename__ = "excel_uploads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    total_ordenes = Column(Integer, nullable=False)
    ordenes_validas = Column(Integer, nullable=False)
    ordenes_con_error = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Orden(Base):
    __tablename__ = "ordenes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    excel_upload_id = Column(UUID(as_uuid=True), ForeignKey("excel_uploads.id"), nullable=False)
    cliente_nombre = Column(String(255), nullable=False)
    cliente_email = Column(EncryptedString(512), nullable=False)
    cuenta_comitente = Column(EncryptedString(256), nullable=False)
    cuenta_cotapartista = Column(EncryptedString(256), nullable=False)
    instrumento = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoOperacion), nullable=False)
    cantidad = Column(Numeric(18, 4), nullable=False)
    precio = Column(Numeric(18, 4), nullable=False)
    moneda = Column(String(10), nullable=False)
    liquidacion = Column(Enum(CondicionLiquidacion), nullable=False)
    fecha_operacion = Column(DateTime, nullable=False)
    dj_aplicada = Column(Boolean, default=False, nullable=False)
    dj_tipo = Column(String(100), nullable=True)
    estado = Column(Enum(EstadoMinuta), default=EstadoMinuta.BORRADOR, nullable=False)
    texto_minuta = Column(Text, nullable=False)
    texto_editado = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
