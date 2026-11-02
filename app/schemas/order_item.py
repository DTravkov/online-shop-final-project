from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    order_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class OrderItemUpdate(OrderItemCreate):
    pass


class OrderItemRead(OrderItemCreate):
    model_config = ConfigDict(from_attributes=True)

    order_item_id: int
