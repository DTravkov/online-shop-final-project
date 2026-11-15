from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.fulfillment import Fulfillment
from app.models.seller import Seller


class FulfillmentRepository:
    """Writes participate in the order repository's transaction."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, order_id: int, seller_id: int) -> Fulfillment:
        record = Fulfillment(order_id=order_id, seller_id=seller_id, status="new")
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_for_orders(self, order_ids: list[int]) -> list[tuple[Fulfillment, Seller]]:
        if not order_ids:
            return []
        result = await self.db.execute(
            select(Fulfillment, Seller)
            .join(Seller, Seller.seller_id == Fulfillment.seller_id)
            .where(Fulfillment.order_id.in_(order_ids))
            .order_by(Fulfillment.seller_id)
        )
        return [tuple(row) for row in result.all()]

    async def get(self, order_id: int, seller_id: int) -> Fulfillment | None:
        return await self.db.scalar(select(Fulfillment).where(
            Fulfillment.order_id == order_id, Fulfillment.seller_id == seller_id,
        ))

    async def set_status(self, record: Fulfillment, status: str) -> None:
        record.status = status
        await self.db.flush()


def get_fulfillment_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> FulfillmentRepository:
    return FulfillmentRepository(db)
