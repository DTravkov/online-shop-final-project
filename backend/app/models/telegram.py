from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TelegramLink(Base):
    __tablename__ = "telegram_links"

    link_id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id", ondelete="CASCADE"), unique=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)


class TelegramNotification(Base):
    __tablename__ = "telegram_notifications"
    __table_args__ = (
        Index("ix_telegram_pending_chat", "chat_id", "notification_id", postgresql_where=text("finished_at IS NULL")),
    )

    notification_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    order_id: Mapped[int]
    event: Mapped[str] = mapped_column(String(32))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    lease_id: Mapped[UUID | None]
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(16))
