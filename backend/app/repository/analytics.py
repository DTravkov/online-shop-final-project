from decimal import Decimal
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.account import Account
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.seller import Seller

# Sales that count toward analytics: not cancelled and not refunded.
_COUNTED_ORDER = (Order.order_status != "cancelled") & (Order.payment_status != "refunded")


class AnalyticsRepository:
    """Read-only aggregate queries for the administrator dashboard."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def top_products(self, limit: int) -> list[dict[str, Any]]:
        units_sold = func.sum(OrderItem.quantity).label("units_sold")
        revenue = func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue")
        result = await self.db.execute(
            select(
                Product.product_id,
                Product.product_name,
                Seller.seller_id,
                Seller.store_name,
                units_sold,
                revenue,
            )
            .join(OrderItem, OrderItem.product_id == Product.product_id)
            .join(Order, Order.order_id == OrderItem.order_id)
            .join(Seller, Seller.seller_id == Product.seller_id)
            .where(_COUNTED_ORDER)
            .group_by(Product.product_id, Product.product_name, Seller.seller_id, Seller.store_name)
            .order_by(units_sold.desc(), revenue.desc(), Product.product_id)
            .limit(limit)
        )
        return [dict(row._mapping) for row in result.all()]

    async def count(self, model, *conditions) -> int:
        query = select(func.count()).select_from(model)
        if conditions:
            query = query.where(*conditions)
        return int(await self.db.scalar(query) or 0)

    async def count_accounts(self) -> int:
        return await self.count(Account)

    async def count_customers(self) -> int:
        return await self.count(Customer)

    async def count_sellers(self) -> int:
        return await self.count(Seller)

    async def product_counts(self) -> tuple[int, int, int]:
        total = await self.count(Product)
        active = await self.count(Product, Product.is_active.is_(True))
        out_of_stock = await self.count(Product, Product.is_active.is_(True), Product.stock_quantity == 0)
        return total, active, out_of_stock

    async def _orders_grouped_by(self, column) -> dict[str, int]:
        result = await self.db.execute(select(column, func.count()).group_by(column))
        return {status: int(total) for status, total in result.all()}

    async def orders_by_status(self) -> dict[str, int]:
        return await self._orders_grouped_by(Order.order_status)

    async def orders_by_payment_status(self) -> dict[str, int]:
        return await self._orders_grouped_by(Order.payment_status)

    async def items_sold(self) -> int:
        return int(
            await self.db.scalar(
                select(func.coalesce(func.sum(OrderItem.quantity), 0))
                .join(Order, Order.order_id == OrderItem.order_id)
                .where(_COUNTED_ORDER)
            )
            or 0
        )

    async def paid_revenue(self) -> tuple[Decimal, int]:
        total, orders = (
            await self.db.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0), func.count()).where(
                    Order.payment_status == "paid", Order.order_status != "cancelled"
                )
            )
        ).one()
        return Decimal(total), int(orders)


def get_analytics_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyticsRepository:
    return AnalyticsRepository(db)
