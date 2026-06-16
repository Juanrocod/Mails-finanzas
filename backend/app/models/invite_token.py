# backend/app/models/invite_token.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class InviteToken(Base):
    __tablename__ = "invite_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)
    tipo = Column(String(10), nullable=False)  # 'invite' | 'reset'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expira_en = Column(DateTime(timezone=True), nullable=False)
    usado_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
