from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.models.order import Order
from app.repository.cart_item import CartItemRepository, get_cart_item_repository
from app.repository.customer import CustomerRepository, get_customer_repository
from app.repository.fulfillment import FulfillmentRepository, get_fulfillment_repository
from app.repository.order import OrderRepository, get_order_repository
from app.repository.order_item import OrderItemRepository, get_order_item_repository
from app.repository.product import ProductRepository, get_product_repository
from app.repository.telegram import TelegramRepository, get_telegram_repository
from app.schemas.order import CheckoutRequest, FulfillmentRead, OrderDetail, OrderItemDetail, OrderRead
from app.service.cart import check_stock
from app.service.wallet import WalletService, get_wallet_service

MAX_ORDER_TOTAL = Decimal("99999999.99")  # orders.total_amount is NUMERIC(10, 2)
CENT = Decimal("0.01")


async def load_order_details(
    order_items: OrderItemRepository, fulfillments: FulfillmentRepository, orders: list[Order]
) -> list[OrderDetail]:
    """Attach items and seller fulfillments with batched queries."""
    items_by_order: dict[int, list[OrderItemDetail]] = defaultdict(list)
    for item, product, seller in await order_items.list_details([order.order_id for order in orders]):
        items_by_order[item.order_id].append(OrderItemDetail.from_row(item, product, seller))
    groups: dict[int, list[FulfillmentRead]] = defaultdict(list)
    for fulfillment, seller in await fulfillments.list_for_orders([order.order_id for order in orders]):
        groups[fulfillment.order_id].append(FulfillmentRead(
            fulfillment_id=fulfillment.fulfillment_id,
            seller_id=seller.seller_id,
            store_name=seller.store_name,
            status=fulfillment.status,
        ))
    return [
        OrderDetail(
            **OrderRead.model_validate(order).model_dump(),
            items=items_by_order[order.order_id], fulfillments=groups[order.order_id],
        )
        for order in orders
    ]


class CustomerOrderService:
    def __init__(
        self,
        orders: OrderRepository,
        order_items: OrderItemRepository,
        cart: CartItemRepository,
        products: ProductRepository,
        customers: CustomerRepository,
        fulfillments: FulfillmentRepository,
        wallet: WalletService,
        telegram: TelegramRepository,
    ):
        self.orders = orders
        self.order_items = order_items
        self.cart = cart
        self.products = products
        self.customers = customers
        self.fulfillments = fulfillments
        self.wallet = wallet
        self.telegram = telegram

    async def checkout(self, customer_id: int, data: CheckoutRequest) -> OrderDetail:
        """Turn the cart into one order: snapshot prices, reserve stock, empty the cart."""
        async with self.orders.transaction():
            customer = await self.customers.get_for_update(customer_id)
            if customer is None:
                raise RecordNotFound("Customer", customer_id)
            cart_items = await self.cart.list(customer_id)
            if not cart_items:
                raise BusinessRuleViolation("Cart is empty.")

            locked = await self.products.get_many_for_update([item.product_id for item in cart_items])
            products = {product.product_id: product for product in locked}
            total = Decimal("0.00")
            for item in cart_items:
                product = products.get(item.product_id)
                if product is None or not product.is_active:
                    raise BusinessRuleViolation(f"Product {item.product_id} is no longer available.")
                check_stock(product, item.quantity)
                total += product.price * item.quantity
            total = total.quantize(CENT)
            if total > MAX_ORDER_TOTAL:
                raise BusinessRuleViolation("Order total exceeds the maximum allowed amount.")

            order = await self.orders.create({
                "customer_id": customer_id,
                "order_date": datetime.now(UTC),
                "total_amount": total,
                "order_status": "new",
                "payment_status": "pending",
                "delivery_address": data.delivery_address or customer.delivery_address,
            })
            groups = {}
            for seller_id in sorted({product.seller_id for product in products.values()}):
                groups[seller_id] = await self.fulfillments.create(order.order_id, seller_id)
            for item in cart_items:
                product = products[item.product_id]
                await self.order_items.create({
                    "order_id": order.order_id,
                    "product_id": product.product_id,
                    "fulfillment_id": groups[product.seller_id].fulfillment_id,
                    "quantity": item.quantity,
                    "unit_price": product.price,
                })
                await self.products.update(product, {"stock_quantity": product.stock_quantity - item.quantity})
            if data.payment_status == "paid":
                await self.wallet.charge_order(order)
                order = await self.orders.update(order, {"payment_status": "paid"})
            await self.cart.clear(customer_id)
            await self.telegram.enqueue(order.order_id, "seller_new_order", datetime.now(UTC), seller_ids=list(groups))
            return (await load_order_details(self.order_items, self.fulfillments, [order]))[0]

    async def list_orders(
        self, customer_id: int, order_status: str | None, offset: int, limit: int
    ) -> list[OrderDetail]:
        orders = await self.orders.list_filtered(
            offset, limit, customer_id=customer_id, order_status=order_status
        )
        return await load_order_details(self.order_items, self.fulfillments, orders)

    async def _get_own_order(self, customer_id: int, order_id: int, for_update: bool = False) -> Order:
        if for_update:
            order = await self.orders.get_for_update(order_id)
        else:
            order = await self.orders.get(order_id)
        if order is None or order.customer_id != customer_id:
            raise RecordNotFound("Order", order_id)
        return order

    async def get_order(self, customer_id: int, order_id: int) -> OrderDetail:
        order = await self._get_own_order(customer_id, order_id)
        return (await load_order_details(self.order_items, self.fulfillments, [order]))[0]

    async def pay(self, customer_id: int, order_id: int) -> OrderDetail:
        """Pay from the buyer balance and credit each seller atomically."""
        async with self.orders.transaction():
            order = await self._get_own_order(customer_id, order_id, for_update=True)
            if order.order_status == "cancelled":
                raise BusinessRuleViolation("A cancelled order cannot be paid.")
            if order.payment_status != "pending":
                raise BusinessRuleViolation(f"Order payment is already {order.payment_status}.")
            await self.wallet.charge_order(order)
            order = await self.orders.update(order, {"payment_status": "paid"})
            await self.telegram.enqueue(order.order_id, "paid", datetime.now(UTC), customer_id=customer_id)
            return (await load_order_details(self.order_items, self.fulfillments, [order]))[0]

    async def cancel(self, customer_id: int, order_id: int) -> OrderDetail:
        """Cancel a new order, return its stock, and refund it if it was paid."""
        async with self.orders.transaction():
            order = await self._get_own_order(customer_id, order_id, for_update=True)
            if order.order_status != "new":
                raise BusinessRuleViolation(f"Only new orders can be cancelled; this one is {order.order_status}.")
            items = await self.order_items.list_for_order(order_id)
            locked = await self.products.get_many_for_update([item.product_id for item in items])
            products = {product.product_id: product for product in locked}
            for item in items:
                product = products[item.product_id]
                await self.products.update(product, {"stock_quantity": product.stock_quantity + item.quantity})
            for fulfillment, _seller in await self.fulfillments.list_for_orders([order_id]):
                await self.fulfillments.set_status(fulfillment, "cancelled")
            values = {"order_status": "cancelled"}
            if order.payment_status == "paid":
                await self.wallet.refund_order(order)
                values["payment_status"] = "refunded"
            order = await self.orders.update(order, values)
            await self.telegram.enqueue(order.order_id, "cancelled", datetime.now(UTC), customer_id=customer_id)
            return (await load_order_details(self.order_items, self.fulfillments, [order]))[0]


def get_customer_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    order_items: Annotated[OrderItemRepository, Depends(get_order_item_repository)],
    cart: Annotated[CartItemRepository, Depends(get_cart_item_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    customers: Annotated[CustomerRepository, Depends(get_customer_repository)],
    fulfillments: Annotated[FulfillmentRepository, Depends(get_fulfillment_repository)],
    wallet: Annotated[WalletService, Depends(get_wallet_service)],
    telegram: Annotated[TelegramRepository, Depends(get_telegram_repository)],
) -> CustomerOrderService:
    return CustomerOrderService(orders, order_items, cart, products, customers, fulfillments, wallet, telegram)
