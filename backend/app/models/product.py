from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.seller_id"))
    product_name: Mapped[str] = mapped_column(String(150))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock_quantity: Mapped[int] = mapped_column()
    # False once a seller withdraws the product; order history keeps referencing it.
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
