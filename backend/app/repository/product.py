from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.product import Product


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Product conflicts with related records.") from exc

    async def list(self, offset: int, limit: int) -> list[Product]:
        result = await self.db.scalars(
            select(Product).order_by(Product.product_id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, product_id: int) -> Product | None:
        return await self.db.get(Product, product_id)

    async def create(self, values: dict[str, Any]) -> Product:
        record = Product(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: Product, values: dict[str, Any]) -> Product:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: Product) -> None:
        await self.db.delete(record)
        await self.db.flush()


def get_product_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ProductRepository:
    return ProductRepository(db)
