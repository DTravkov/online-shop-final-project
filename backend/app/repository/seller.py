from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.seller import Seller


class SellerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Seller conflicts with related records.") from exc

    async def list(self, offset: int, limit: int) -> list[Seller]:
        result = await self.db.scalars(
            select(Seller).order_by(Seller.seller_id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, seller_id: int) -> Seller | None:
        return await self.db.get(Seller, seller_id)

    async def get_for_update(self, seller_id: int) -> Seller | None:
        return await self.db.get(Seller, seller_id, with_for_update=True)

    async def create(self, values: dict[str, Any]) -> Seller:
        record = Seller(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: Seller, values: dict[str, Any]) -> Seller:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: Seller) -> None:
        await self.db.delete(record)
        await self.db.flush()


def get_seller_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> SellerRepository:
    return SellerRepository(db)
