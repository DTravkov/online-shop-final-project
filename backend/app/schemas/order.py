from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

OrderStatus = Literal["new", "shipped", "delivered", "cancelled"]
PaymentStatus = Literal["paid", "pending", "refunded"]


class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    order_date: AwareDatetime
    total_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    order_status: OrderStatus
    payment_status: PaymentStatus
    delivery_address: str | None = Field(default=None, min_length=1, max_length=255)


class OrderUpdate(OrderCreate):
    pass


class OrderRead(OrderCreate):
    model_config = ConfigDict(from_attributes=True)

    order_id: int


class CheckoutRequest(BaseModel):
    # Omit to deliver to the customer's default delivery address.
    delivery_address: str | None = Field(default=None, min_length=1, max_length=255)
    # Payment simulation: "paid" pays immediately, "pending" pays later.
    payment_status: Literal["paid", "pending"] = "pending"


class OrderItemDetail(BaseModel):
    order_item_id: int
    product_id: int
    product_name: str
    seller_id: int
    store_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    @classmethod
    def from_row(cls, item, product, seller) -> "OrderItemDetail":
        return cls(
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            product_name=product.product_name,
            seller_id=seller.seller_id,
            store_name=seller.store_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.unit_price * item.quantity,
        )


class OrderDetail(OrderRead):
    items: list[OrderItemDetail]


class SellerOrderRead(BaseModel):
    order_id: int
    order_date: datetime
    order_status: OrderStatus
    payment_status: PaymentStatus
    delivery_address: str | None
    customer_name: str
    # Only this seller's items in the order.
    items: list[OrderItemDetail]
    seller_total: Decimal


class OrderStatusUpdate(BaseModel):
    order_status: Literal["shipped", "delivered"]


class PaymentStatusUpdate(BaseModel):
    payment_status: PaymentStatus
