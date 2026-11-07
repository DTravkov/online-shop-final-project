from collections import defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.models.order import Order
from app.repository.customer import CustomerRepository, get_customer_repository
from app.repository.order import OrderRepository, get_order_repository
from app.repository.order_item import OrderItemRepository, get_order_item_repository
from app.schemas.order import OrderItemDetail, OrderStatusUpdate, SellerOrderRead

# Statuses a seller may move an order to, by current status.
SELLER_STATUS_TRANSITIONS = {
    "new": {"shipped", "delivered"},
    "shipped": {"delivered"},
}


class SellerOrderService:
    """Orders that contain at least one of the signed-in seller's products."""

    def __init__(
        self,
        orders: OrderRepository,
        order_items: OrderItemRepository,
        customers: CustomerRepository,
    ):
        self.orders = orders
        self.order_items = order_items
        self.customers = customers

    async def _to_read(self, seller_id: int, orders: list[Order]) -> list[SellerOrderRead]:
        items_by_order: dict[int, list[OrderItemDetail]] = defaultdict(list)
        rows = await self.order_items.list_details([order.order_id for order in orders], seller_id=seller_id)
        for item, product, seller in rows:
            items_by_order[item.order_id].append(OrderItemDetail.from_row(item, product, seller))
        names: dict[int, str] = {}
        for customer_id in {order.customer_id for order in orders}:
            customer = await self.customers.get(customer_id)
            names[customer_id] = customer.full_name if customer is not None else ""
        return [
            SellerOrderRead(
                order_id=order.order_id,
                order_date=order.order_date,
                order_status=order.order_status,
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
        if order is None or not await self.orders.contains_seller_items(order_id, seller_id):
            raise RecordNotFound("Order", order_id)
        return order

    async def get_order(self, seller_id: int, order_id: int) -> SellerOrderRead:
        order = await self._get_order(seller_id, order_id)
        return (await self._to_read(seller_id, [order]))[0]

    async def update_status(self, seller_id: int, order_id: int, data: OrderStatusUpdate) -> SellerOrderRead:
        async with self.orders.transaction():
            order = await self._get_order(seller_id, order_id, for_update=True)
            allowed = SELLER_STATUS_TRANSITIONS.get(order.order_status, set())
            if data.order_status not in allowed:
                raise BusinessRuleViolation(
                    f"Cannot change order status from {order.order_status} to {data.order_status}."
                )
            order = await self.orders.update(order, {"order_status": data.order_status})
            return (await self._to_read(seller_id, [order]))[0]


def get_seller_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    order_items: Annotated[OrderItemRepository, Depends(get_order_item_repository)],
    customers: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> SellerOrderService:
    return SellerOrderService(orders, order_items, customers)
