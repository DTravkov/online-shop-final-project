from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.customer import Customer
from app.models.fulfillment import Fulfillment
from app.models.order import Order
from app.models.seller_review import SellerReview


class SellerReviewRepository:
    """Review writes share a seller transaction, including its rating update."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_seller(self, seller_id: int, offset: int, limit: int) -> list[tuple[SellerReview, str]]:
        result = await self.db.execute(
            select(SellerReview, Customer.full_name)
            .join(Customer, Customer.customer_id == SellerReview.customer_id)
            .where(SellerReview.seller_id == seller_id)
            .order_by(SellerReview.created_at.desc(), SellerReview.review_id.desc()).offset(offset).limit(limit)
        )
        return [tuple(row) for row in result.all()]

    async def get(self, customer_id: int, seller_id: int) -> SellerReview | None:
        return await self.db.scalar(select(SellerReview).where(
            SellerReview.customer_id == customer_id, SellerReview.seller_id == seller_id,
        ))

    async def eligible(self, customer_id: int, seller_id: int) -> bool:
        return await self.db.scalar(
            select(Fulfillment.fulfillment_id)
            .join(Order, Order.order_id == Fulfillment.order_id)
            .where(
                Order.customer_id == customer_id, Order.payment_status == "paid", Order.order_status != "cancelled",
                Fulfillment.seller_id == seller_id, Fulfillment.status == "delivered",
            ).limit(1)
        ) is not None

    async def save(self, customer_id: int, seller_id: int, rating: int, comment: str) -> SellerReview:
        record = await self.get(customer_id, seller_id)
        if record is None:
            record = SellerReview(customer_id=customer_id, seller_id=seller_id, rating=rating, comment=comment)
            self.db.add(record)
        else:
            record.rating = rating
            record.comment = comment
            record.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: SellerReview) -> None:
        await self.db.delete(record)
        await self.db.flush()

    async def stats(self, seller_id: int) -> tuple[Decimal, int]:
        average, count = (await self.db.execute(
            select(func.coalesce(func.avg(SellerReview.rating), 0), func.count())
            .where(SellerReview.seller_id == seller_id)
        )).one()
        return Decimal(str(average)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), int(count)


def get_seller_review_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> SellerReviewRepository:
    return SellerReviewRepository(db)
