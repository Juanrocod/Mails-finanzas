from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, String, DateTime
from app.core.database import Base


class ConfigFiltros(Base):
    __tablename__ = "config_filtros_minutas"
    id = Column(Integer, primary_key=True, default=1)
    reglas = Column(Text, nullable=False, default="[]")
    logica = Column(String(3), nullable=False, default="OR")
    actualizado_en = Column(DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
