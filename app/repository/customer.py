from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Customer conflicts with related records.") from exc

    async def list(self, offset: int, limit: int) -> list[Customer]:
        result = await self.db.scalars(
            select(Customer).order_by(Customer.customer_id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, customer_id: int) -> Customer | None:
        return await self.db.get(Customer, customer_id)

    async def create(self, values: dict[str, Any]) -> Customer:
        record = Customer(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: Customer, values: dict[str, Any]) -> Customer:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: Customer) -> None:
        await self.db.delete(record)
        await self.db.flush()


def get_customer_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> CustomerRepository:
    return CustomerRepository(db)
