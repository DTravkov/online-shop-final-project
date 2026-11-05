from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
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


def get_order_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> OrderRepository:
    return OrderRepository(db)
