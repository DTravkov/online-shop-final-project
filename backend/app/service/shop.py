from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.models.seller_review import SellerReview
from app.repository.customer import CustomerRepository, get_customer_repository
from app.repository.seller import SellerRepository, get_seller_repository
from app.repository.seller_review import SellerReviewRepository, get_seller_review_repository
from app.schemas.seller import PublicSeller
from app.schemas.seller_review import ReviewEligibility, SellerReviewRead, SellerReviewWrite


class ShopService:
    def __init__(self, sellers: SellerRepository, reviews: SellerReviewRepository, customers: CustomerRepository):
        self.sellers = sellers
        self.reviews = reviews
        self.customers = customers

    async def _seller(self, seller_id: int, for_update: bool = False):
        seller = await (self.sellers.get_for_update(seller_id) if for_update else self.sellers.get(seller_id))
        if seller is None:
            raise RecordNotFound("Seller", seller_id)
        return seller

    async def get_shop(self, seller_id: int) -> PublicSeller:
        seller = await self._seller(seller_id)
        rating, count = await self.reviews.stats(seller_id)
        return PublicSeller(seller_id=seller_id, store_name=seller.store_name, rating=rating, review_count=count)

    async def list_reviews(self, seller_id: int, offset: int, limit: int) -> list[SellerReviewRead]:
        await self._seller(seller_id)
        rows = await self.reviews.list_for_seller(seller_id, offset, limit)
        return [self._read(record, name) for record, name in rows]

    @staticmethod
    def _read(record: SellerReview, name: str) -> SellerReviewRead:
        return SellerReviewRead(
            review_id=record.review_id, seller_id=record.seller_id, rating=record.rating, comment=record.comment,
            created_at=record.created_at, updated_at=record.updated_at, customer_name=name,
        )

    async def eligibility(self, customer_id: int, seller_id: int) -> ReviewEligibility:
        await self._seller(seller_id)
        review = await self.reviews.get(customer_id, seller_id)
        customer = await self.customers.get(customer_id)
        if customer is None:
            raise RecordNotFound("Customer", customer_id)
        return ReviewEligibility(
            can_review=await self.reviews.eligible(customer_id, seller_id),
            review=self._read(review, customer.full_name) if review is not None else None,
        )

    async def save_review(self, customer_id: int, seller_id: int, data: SellerReviewWrite) -> SellerReviewRead:
        # Serialize reviews for a shop so concurrent ratings cannot overwrite its average.
        async with self.sellers.transaction():
            # Use the same customer-first lock order as checkout before taking a seller lock.
            customer = await self.customers.get_for_update(customer_id)
            if customer is None:
                raise RecordNotFound("Customer", customer_id)
            seller = await self._seller(seller_id, for_update=True)
            if not await self.reviews.eligible(customer_id, seller_id):
                raise BusinessRuleViolation("Reviews require a paid, delivered purchase from this seller.")
            record = await self.reviews.save(customer_id, seller_id, data.rating, data.comment)
            rating, _count = await self.reviews.stats(seller_id)
            await self.sellers.update(seller, {"rating": rating})
            return self._read(record, customer.full_name)

    async def delete_review(self, customer_id: int, seller_id: int) -> None:
        async with self.sellers.transaction():
            seller = await self._seller(seller_id, for_update=True)
            record = await self.reviews.get(customer_id, seller_id)
            if record is None:
                raise RecordNotFound("Review for seller", seller_id)
            await self.reviews.delete(record)
            rating, _count = await self.reviews.stats(seller_id)
            await self.sellers.update(seller, {"rating": rating})


def get_shop_service(
    sellers: Annotated[SellerRepository, Depends(get_seller_repository)],
    reviews: Annotated[SellerReviewRepository, Depends(get_seller_review_repository)],
    customers: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> ShopService:
    return ShopService(sellers, reviews, customers)
