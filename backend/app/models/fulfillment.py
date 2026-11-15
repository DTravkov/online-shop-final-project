from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Fulfillment(Base):
    """The part of an order fulfilled by one seller."""

    __tablename__ = "fulfillments"
    __table_args__ = (
        UniqueConstraint("order_id", "seller_id"),
        CheckConstraint("status IN ('new', 'shipped', 'delivered', 'cancelled')"),
    )

    fulfillment_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.seller_id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="new")
