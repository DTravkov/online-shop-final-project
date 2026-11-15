from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SellerReview(Base):
    __tablename__ = "seller_reviews"
    __table_args__ = (
        UniqueConstraint("customer_id", "seller_id"),
        CheckConstraint("rating BETWEEN 1 AND 5"),
    )

    review_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.seller_id"), index=True)
    rating: Mapped[int] = mapped_column()
    comment: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
