from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SellerRating(Base):
    __tablename__ = "seller_ratings"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_seller_ratings_rating_range"),
        UniqueConstraint("order_id", "seller_id", name="uq_seller_ratings_order_seller"),
    )

    rating_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.seller_id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer)