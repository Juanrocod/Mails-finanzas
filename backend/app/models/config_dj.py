from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, Text, String, DateTime
from app.core.database import Base


class ConfigDJ(Base):
    __tablename__ = "config_dj"
    id = Column(Integer, primary_key=True, default=1)
    activa = Column(Boolean, nullable=False, default=False)
    incluir_texto_en_minuta = Column(Boolean, nullable=False, default=False)
    texto_alerta = Column(Text, nullable=False, default="")
    reglas = Column(Text, nullable=False, default="[]")
    logica = Column(String(3), nullable=False, default="OR")
    activar_si_requiere_conformidad = Column(Boolean, nullable=False, default=True)
    actualizado_en = Column(DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
