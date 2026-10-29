"""Modelos del módulo bot: Conversaciones y Mensajes de WhatsApp."""

import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.uuid7 import generate_uuid7


class BotConversation(Base):
    """Sesión o conversación con un número de WhatsApp."""

    __tablename__ = "bot_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    messages: Mapped[list["BotMessage"]] = relationship(
        "BotMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class BotMessage(Base):
    """Mensajes individuales entrantes y salientes."""

    __tablename__ = "bot_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid7
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bot_conversations.id", ondelete="RESTRICT"), nullable=False
    )
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # INBOUND, OUTBOUND
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )

    conversation: Mapped["BotConversation"] = relationship(
        "BotConversation", back_populates="messages"
    )
