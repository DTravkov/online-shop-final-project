# Methods named "list" shadow the builtin inside the class body; defer annotations.
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.seller import Seller


class CartItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Cart item conflicts with related records.") from exc

    async def list(self, customer_id: int) -> list[CartItem]:
        result = await self.db.scalars(
            select(CartItem).where(CartItem.customer_id == customer_id).order_by(CartItem.cart_item_id)
        )
        return list(result.all())

    async def list_with_products(self, customer_id: int) -> list[tuple[CartItem, Product, Seller]]:
        result = await self.db.execute(
            select(CartItem, Product, Seller)
            .join(Product, Product.product_id == CartItem.product_id)
            .join(Seller, Seller.seller_id == Product.seller_id)
            .where(CartItem.customer_id == customer_id)
            .order_by(CartItem.cart_item_id)
        )
        return [tuple(row) for row in result.all()]

    async def get(self, customer_id: int, product_id: int) -> CartItem | None:
        return await self.db.scalar(
            select(CartItem).where(CartItem.customer_id == customer_id, CartItem.product_id == product_id)
        )

    async def create(self, values: dict[str, Any]) -> CartItem:
        record = CartItem(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: CartItem, values: dict[str, Any]) -> CartItem:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: CartItem) -> None:
        await self.db.delete(record)
        await self.db.flush()

    async def clear(self, customer_id: int) -> None:
        await self.db.execute(delete(CartItem).where(CartItem.customer_id == customer_id))

    async def delete_for_product(self, product_id: int) -> None:
        await self.db.execute(delete(CartItem).where(CartItem.product_id == product_id))


def get_cart_item_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> CartItemRepository:
    return CartItemRepository(db)
