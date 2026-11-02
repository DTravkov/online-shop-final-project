from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    seller_id: int = Field(gt=0)
    product_name: str = Field(min_length=1, max_length=150)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int = Field(ge=0)


class ProductUpdate(ProductCreate):
    pass


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
