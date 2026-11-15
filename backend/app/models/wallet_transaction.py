from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WalletTransaction(Base):
    """An immutable balance movement; order entries also snapshot seller payouts."""

    __tablename__ = "wallet_transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "order_id", "kind"),
        CheckConstraint("kind IN ('deposit', 'payment', 'sale', 'refund', 'sale_refund')"),
    )

    transaction_id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.order_id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
