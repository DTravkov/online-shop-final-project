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
    is_active: bool = True


class SellerProductCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=150)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int = Field(ge=0)


class SellerProductUpdate(BaseModel):
    """Partial update. Send is_active=true to return a withdrawn product to sale."""

    product_name: str | None = Field(default=None, min_length=1, max_length=150)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductOffer(BaseModel):
    product_id: int
    seller_id: int
    store_name: str
    seller_rating: Decimal
    price: Decimal
    stock_quantity: int


class CatalogProduct(BaseModel):
    product_id: int
    product_name: str
    price: Decimal
    stock_quantity: int
    in_stock: bool
    seller_id: int
    store_name: str
    seller_rating: Decimal


class ProductCard(CatalogProduct):
    # Every active listing with the same name (case-insensitive), cheapest first.
    offers: list[ProductOffer]
