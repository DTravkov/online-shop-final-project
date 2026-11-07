from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.repository.analytics import AnalyticsRepository, get_analytics_repository
from app.repository.order import OrderRepository, get_order_repository
from app.repository.order_item import OrderItemRepository, get_order_item_repository
from app.schemas.analytics import OrderStats, PlatformSummary, ProductStats, TopProduct, UserStats
from app.schemas.order import OrderDetail, OrderRead, PaymentStatusUpdate
from app.service.customer_order import CENT, load_order_details

ORDER_STATUSES = ("new", "shipped", "delivered", "cancelled")
PAYMENT_STATUSES = ("pending", "paid", "refunded")

# Payment statuses an administrator may set, by current status.
PAYMENT_TRANSITIONS = {
    "pending": {"paid"},
    "paid": {"refunded"},
}


class AdminService:
    def __init__(
        self,
        analytics: AnalyticsRepository,
        orders: OrderRepository,
        order_items: OrderItemRepository,
    ):
        self.analytics = analytics
        self.orders = orders
        self.order_items = order_items

    async def top_products(self, limit: int) -> list[TopProduct]:
        return [TopProduct(**row) for row in await self.analytics.top_products(limit)]

    async def summary(self) -> PlatformSummary:
        total_products, active_products, out_of_stock = await self.analytics.product_counts()
        by_order_status = await self.analytics.orders_by_status()
        by_payment_status = await self.analytics.orders_by_payment_status()
        paid_revenue, paid_orders = await self.analytics.paid_revenue()
        average = (paid_revenue / paid_orders).quantize(CENT) if paid_orders else paid_revenue.quantize(CENT)
        return PlatformSummary(
            users=UserStats(
                customers=await self.analytics.count_customers(),
                sellers=await self.analytics.count_sellers(),
                accounts=await self.analytics.count_accounts(),
            ),
            products=ProductStats(total=total_products, active=active_products, out_of_stock=out_of_stock),
            orders=OrderStats(
                total=sum(by_order_status.values()),
                by_order_status={status: by_order_status.get(status, 0) for status in ORDER_STATUSES},
                by_payment_status={status: by_payment_status.get(status, 0) for status in PAYMENT_STATUSES},
                items_sold=await self.analytics.items_sold(),
                paid_revenue=paid_revenue.quantize(CENT),
                average_paid_order=average,
            ),
        )

    async def list_orders(
        self, order_status: str | None, payment_status: str | None, offset: int, limit: int
    ) -> list[OrderRead]:
        records = await self.orders.list_filtered(
            offset, limit, order_status=order_status, payment_status=payment_status
        )
        return [OrderRead.model_validate(record) for record in records]

    async def get_order(self, order_id: int) -> OrderDetail:
        order = await self.orders.get(order_id)
        if order is None:
            raise RecordNotFound("Order", order_id)
        return (await load_order_details(self.order_items, [order]))[0]

    async def update_payment_status(self, order_id: int, data: PaymentStatusUpdate) -> OrderRead:
        async with self.orders.transaction():
            order = await self.orders.get_for_update(order_id)
            if order is None:
                raise RecordNotFound("Order", order_id)
            allowed = PAYMENT_TRANSITIONS.get(order.payment_status, set())
            if data.payment_status not in allowed:
                raise BusinessRuleViolation(
                    f"Cannot change payment status from {order.payment_status} to {data.payment_status}."
                )
            if order.order_status == "cancelled" and data.payment_status == "paid":
                raise BusinessRuleViolation("A cancelled order cannot be paid.")
            order = await self.orders.update(order, {"payment_status": data.payment_status})
            return OrderRead.model_validate(order)


def get_admin_service(
    analytics: Annotated[AnalyticsRepository, Depends(get_analytics_repository)],
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    order_items: Annotated[OrderItemRepository, Depends(get_order_item_repository)],
) -> AdminService:
    return AdminService(analytics, orders, order_items)
