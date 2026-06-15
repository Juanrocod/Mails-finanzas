from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime
from app.core.database import Base


class Plantilla(Base):
    __tablename__ = "plantilla"
    id = Column(Integer, primary_key=True, default=1)
    texto = Column(Text, nullable=False)
    actualizado_en = Column(DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
