from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, gt=0, le=10_000)


class CartItemQuantity(BaseModel):
    quantity: int = Field(gt=0, le=10_000)


class CartItemRead(BaseModel):
    product_id: int
    product_name: str
    seller_id: int
    store_name: str
    unit_price: Decimal
    quantity: int
    stock_quantity: int
    # False when the product was withdrawn or the stock dropped below the quantity.
    available: bool
    subtotal: Decimal


class CartRead(BaseModel):
    items: list[CartItemRead]
    total_quantity: int
    total_amount: Decimal
    can_checkout: bool
