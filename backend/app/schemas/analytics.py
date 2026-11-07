from decimal import Decimal

from pydantic import BaseModel


class TopProduct(BaseModel):
    product_id: int
    product_name: str
    seller_id: int
    store_name: str
    units_sold: int
    revenue: Decimal


class UserStats(BaseModel):
    customers: int
    sellers: int
    accounts: int


class ProductStats(BaseModel):
    total: int
    active: int
    out_of_stock: int


class OrderStats(BaseModel):
    total: int
    by_order_status: dict[str, int]
    by_payment_status: dict[str, int]
    items_sold: int
    paid_revenue: Decimal
    average_paid_order: Decimal


class PlatformSummary(BaseModel):
    users: UserStats
    products: ProductStats
    orders: OrderStats
