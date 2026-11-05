from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SellerCreate(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    rating: Decimal = Field(ge=0, le=5, max_digits=2, decimal_places=1)


class SellerUpdate(SellerCreate):
    pass


class SellerRead(SellerCreate):
    model_config = ConfigDict(from_attributes=True)

    seller_id: int
