# Methods named "list" shadow the builtin inside the class body; defer annotations.
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.seller import Seller


class OrderItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Order item conflicts with related records.") from exc

    async def list(self, offset: int, limit: int) -> list[OrderItem]:
        result = await self.db.scalars(
            select(OrderItem).order_by(OrderItem.order_item_id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, order_item_id: int) -> OrderItem | None:
        return await self.db.get(OrderItem, order_item_id)

    async def create(self, values: dict[str, Any]) -> OrderItem:
        record = OrderItem(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: OrderItem, values: dict[str, Any]) -> OrderItem:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: OrderItem) -> None:
        await self.db.delete(record)
        await self.db.flush()

    async def list_for_order(self, order_id: int) -> list[OrderItem]:
        result = await self.db.scalars(
            select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.order_item_id)
        )
        return list(result.all())

    async def list_details(
        self, order_ids: list[int], seller_id: int | None = None
    ) -> list[tuple[OrderItem, Product, Seller]]:
        """Items of the given orders with product and seller data, optionally one seller's only."""
        if not order_ids:
            return []
        query = (
            select(OrderItem, Product, Seller)
            .join(Product, Product.product_id == OrderItem.product_id)
            .join(Seller, Seller.seller_id == Product.seller_id)
            .where(OrderItem.order_id.in_(order_ids))
        )
        if seller_id is not None:
            query = query.where(Product.seller_id == seller_id)
        result = await self.db.execute(query.order_by(OrderItem.order_item_id))
        return [tuple(row) for row in result.all()]


def get_order_item_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> OrderItemRepository:
    return OrderItemRepository(db)
