from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Account(Base):
    """Login credentials and role. Customer and seller profiles stay in their own tables."""

    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.customer_id", ondelete="CASCADE"), unique=True
    )
    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("sellers.seller_id", ondelete="CASCADE"), unique=True
    )
