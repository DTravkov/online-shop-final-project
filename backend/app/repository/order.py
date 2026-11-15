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
from app.models.fulfillment import Fulfillment
from app.models.order import Order


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Order conflicts with related records.") from exc

    async def list(self, offset: int, limit: int) -> list[Order]:
        result = await self.db.scalars(
            select(Order).order_by(Order.order_id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, order_id: int) -> Order | None:
        return await self.db.get(Order, order_id)

    async def create(self, values: dict[str, Any]) -> Order:
        record = Order(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: Order, values: dict[str, Any]) -> Order:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: Order) -> None:
        await self.db.delete(record)
        await self.db.flush()

    async def get_for_update(self, order_id: int) -> Order | None:
        return await self.db.get(Order, order_id, with_for_update=True)

    async def list_filtered(
        self,
        offset: int,
        limit: int,
        customer_id: int | None = None,
        order_status: str | None = None,
        payment_status: str | None = None,
    ) -> list[Order]:
        query = select(Order)
        if customer_id is not None:
            query = query.where(Order.customer_id == customer_id)
        if order_status is not None:
            query = query.where(Order.order_status == order_status)
        if payment_status is not None:
            query = query.where(Order.payment_status == payment_status)
        result = await self.db.scalars(query.order_by(Order.order_id.desc()).offset(offset).limit(limit))
        return list(result.all())

    async def list_for_seller(
        self, seller_id: int, order_status: str | None, offset: int, limit: int
    ) -> list[Order]:
        query = select(Order).join(Fulfillment, Fulfillment.order_id == Order.order_id).where(
            Fulfillment.seller_id == seller_id,
        )
        if order_status is not None:
            query = query.where(Fulfillment.status == order_status)
        result = await self.db.scalars(query.order_by(Order.order_id.desc()).offset(offset).limit(limit))
        return list(result.all())



def get_order_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> OrderRepository:
    return OrderRepository(db)
