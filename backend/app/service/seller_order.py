from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.models.order import Order
from app.repository.customer import CustomerRepository, get_customer_repository
from app.repository.fulfillment import FulfillmentRepository, get_fulfillment_repository
from app.repository.order import OrderRepository, get_order_repository
from app.repository.order_item import OrderItemRepository, get_order_item_repository
from app.repository.telegram import TelegramRepository, get_telegram_repository
from app.schemas.order import OrderItemDetail, OrderStatusUpdate, SellerOrderRead

# Statuses a seller may move an order to, by current status.
SELLER_STATUS_TRANSITIONS = {
    "new": {"shipped", "delivered"},
    "shipped": {"delivered"},
}


def overall_status(statuses: list[str]) -> str:
    """Summarize seller progress without claiming the whole order has arrived."""
    states = set(statuses)
    if len(states) == 1:
        return statuses[0]
    if "delivered" in states:
        return "partially_delivered"
    return "partially_shipped"


class SellerOrderService:
    """Orders that contain at least one of the signed-in seller's products."""

    def __init__(
        self,
        orders: OrderRepository,
        order_items: OrderItemRepository,
        customers: CustomerRepository,
        fulfillments: FulfillmentRepository,
        telegram: TelegramRepository,
    ):
        self.orders = orders
        self.order_items = order_items
        self.customers = customers
        self.fulfillments = fulfillments
        self.tg_repo = telegram

    async def _to_read(self, seller_id: int, orders: list[Order]) -> list[SellerOrderRead]:
        items_by_order: dict[int, list[OrderItemDetail]] = defaultdict(list)
        rows = await self.order_items.list_details([order.order_id for order in orders], seller_id=seller_id)
        for item, product, seller in rows:
            items_by_order[item.order_id].append(OrderItemDetail.from_row(item, product, seller))
        names: dict[int, str] = {}
        for customer_id in {order.customer_id for order in orders}:
            customer = await self.customers.get(customer_id)
            names[customer_id] = customer.full_name if customer is not None else ""
        statuses = {
            fulfillment.order_id: fulfillment.status
            for fulfillment, _seller in await self.fulfillments.list_for_orders([order.order_id for order in orders])
            if fulfillment.seller_id == seller_id
        }
        return [
            SellerOrderRead(
                order_id=order.order_id,
                order_date=order.order_date,
                order_status=statuses[order.order_id],
                overall_order_status=order.order_status,
                payment_status=order.payment_status,
                delivery_address=order.delivery_address,
                customer_name=names[order.customer_id],
                items=items_by_order[order.order_id],
                seller_total=sum((item.subtotal for item in items_by_order[order.order_id]), Decimal("0.00")),
            )
            for order in orders
        ]

    async def list_orders(
        self, seller_id: int, order_status: str | None, offset: int, limit: int
    ) -> list[SellerOrderRead]:
        orders = await self.orders.list_for_seller(seller_id, order_status, offset, limit)
        return await self._to_read(seller_id, orders)

    async def _get_order(self, seller_id: int, order_id: int, for_update: bool = False) -> Order:
        order = await (self.orders.get_for_update(order_id) if for_update else self.orders.get(order_id))
        if order is None or await self.fulfillments.get(order_id, seller_id) is None:
            raise RecordNotFound("Order", order_id)
        return order

    async def get_order(self, seller_id: int, order_id: int) -> SellerOrderRead:
        order = await self._get_order(seller_id, order_id)
        return (await self._to_read(seller_id, [order]))[0]

    async def update_status(self, seller_id: int, order_id: int, data: OrderStatusUpdate) -> SellerOrderRead:
        async with self.orders.transaction():
            order = await self._get_order(seller_id, order_id, for_update=True)
            fulfillment = await self.fulfillments.get(order_id, seller_id)
            allowed = SELLER_STATUS_TRANSITIONS.get(fulfillment.status, set())
            if data.order_status not in allowed:
                raise BusinessRuleViolation(
                    f"Cannot change seller fulfillment from {fulfillment.status} to {data.order_status}."
                )
            if order.order_status == "cancelled":
                raise BusinessRuleViolation("A cancelled order cannot be fulfilled.")
            await self.fulfillments.set_status(fulfillment, data.order_status)
            statuses = [record.status for record, _seller in await self.fulfillments.list_for_orders([order_id])]
            new_status = overall_status(statuses)
            if order.order_status != new_status:
                order = await self.orders.update(order, {"order_status": new_status})
                await self.tg_repo.enqueue(
                    order.order_id, new_status, datetime.now(UTC), customer_id=order.customer_id,
                )
            return (await self._to_read(seller_id, [order]))[0]


def get_seller_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    order_items: Annotated[OrderItemRepository, Depends(get_order_item_repository)],
    customers: Annotated[CustomerRepository, Depends(get_customer_repository)],
    fulfillments: Annotated[FulfillmentRepository, Depends(get_fulfillment_repository)],
    telegram: Annotated[TelegramRepository, Depends(get_telegram_repository)],
) -> SellerOrderService:
    return SellerOrderService(orders, order_items, customers, fulfillments, telegram)
