from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.seller_rating import SellerRating


class SellerRatingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Seller rating conflicts with related records.") from exc

    async def get_for_order_seller(self, order_id: int, seller_id: int) -> SellerRating | None:
        return await self.db.scalar(
            select(SellerRating).where(
                SellerRating.order_id == order_id,
                SellerRating.seller_id == seller_id,
            )
        )

    async def list_for_orders(self, order_ids: list[int]) -> list[SellerRating]:
        if not order_ids:
            return []
        result = await self.db.scalars(
            select(SellerRating)
            .where(SellerRating.order_id.in_(order_ids))
            .order_by(SellerRating.order_id, SellerRating.seller_id)
        )
        return list(result.all())

    async def create(self, values: dict[str, Any]) -> SellerRating:
        record = SellerRating(**values)
        self.db.add(record)
        await self.db.flush()
        return record

    async def update(self, record: SellerRating, values: dict[str, Any]) -> SellerRating:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        return record

    async def average_for_seller(self, seller_id: int):
        return await self.db.scalar(
            select(func.avg(SellerRating.rating)).where(SellerRating.seller_id == seller_id)
        )


def get_seller_rating_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SellerRatingRepository:
    return SellerRatingRepository(db)