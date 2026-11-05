from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    order_date: AwareDatetime
    total_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    order_status: Literal["new", "shipped", "delivered", "cancelled"]
    payment_status: Literal["paid", "pending", "refunded"]


class OrderUpdate(OrderCreate):
    pass


class OrderRead(OrderCreate):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
