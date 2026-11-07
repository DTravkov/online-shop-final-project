from decimal import Decimal
from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.models.product import Product
from app.repository.cart_item import CartItemRepository, get_cart_item_repository
from app.repository.product import ProductRepository, get_product_repository
from app.schemas.cart import CartItemAdd, CartItemQuantity, CartItemRead, CartRead


def check_stock(product: Product, quantity: int) -> None:
    if quantity > product.stock_quantity:
        raise BusinessRuleViolation(
            f"Not enough stock for '{product.product_name}': "
            f"requested {quantity}, available {product.stock_quantity}."
        )


class CartService:
    def __init__(self, cart: CartItemRepository, products: ProductRepository):
        self.cart = cart
        self.products = products

    async def get_cart(self, customer_id: int) -> CartRead:
        items = []
        for item, product, seller in await self.cart.list_with_products(customer_id):
            items.append(CartItemRead(
                product_id=product.product_id,
                product_name=product.product_name,
                seller_id=seller.seller_id,
                store_name=seller.store_name,
                unit_price=product.price,
                quantity=item.quantity,
                stock_quantity=product.stock_quantity,
                available=product.is_active and item.quantity <= product.stock_quantity,
                subtotal=product.price * item.quantity,
            ))
        return CartRead(
            items=items,
            total_quantity=sum(item.quantity for item in items),
            total_amount=sum((item.subtotal for item in items), Decimal("0.00")),
            can_checkout=bool(items) and all(item.available for item in items),
        )

    async def _get_sellable_product(self, product_id: int) -> Product:
        product = await self.products.get(product_id)
        if product is None or not product.is_active:
            raise RecordNotFound("Product", product_id)
        return product

    async def add_item(self, customer_id: int, data: CartItemAdd) -> CartRead:
        async with self.cart.transaction():
            product = await self._get_sellable_product(data.product_id)
            item = await self.cart.get(customer_id, data.product_id)
            quantity = data.quantity + (item.quantity if item is not None else 0)
            check_stock(product, quantity)
            if item is None:
                await self.cart.create({
                    "customer_id": customer_id,
                    "product_id": data.product_id,
                    "quantity": quantity,
                })
            else:
                await self.cart.update(item, {"quantity": quantity})
        return await self.get_cart(customer_id)

    async def set_quantity(self, customer_id: int, product_id: int, data: CartItemQuantity) -> CartRead:
        async with self.cart.transaction():
            item = await self.cart.get(customer_id, product_id)
            if item is None:
                raise RecordNotFound("Cart item for product", product_id)
            check_stock(await self._get_sellable_product(product_id), data.quantity)
            await self.cart.update(item, {"quantity": data.quantity})
        return await self.get_cart(customer_id)

    async def remove_item(self, customer_id: int, product_id: int) -> CartRead:
        async with self.cart.transaction():
            item = await self.cart.get(customer_id, product_id)
            if item is None:
                raise RecordNotFound("Cart item for product", product_id)
            await self.cart.delete(item)
        return await self.get_cart(customer_id)

    async def clear(self, customer_id: int) -> None:
        async with self.cart.transaction():
            await self.cart.clear(customer_id)


def get_cart_service(
    cart: Annotated[CartItemRepository, Depends(get_cart_item_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
) -> CartService:
    return CartService(cart, products)
