from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.seller import PublicSeller
from app.schemas.seller_review import ReviewEligibility, SellerReviewRead, SellerReviewWrite
from app.service.auth import CustomerAccount
from app.service.shop import ShopService, get_shop_service

router = APIRouter(tags=["shops and reviews"])
ShopServiceDep = Annotated[ShopService, Depends(get_shop_service)]


@router.get("/catalog/sellers/{seller_id}", response_model=PublicSeller)
async def get_shop(seller_id: int, service: ShopServiceDep):
    return await service.get_shop(seller_id)


@router.get("/catalog/sellers/{seller_id}/reviews", response_model=list[SellerReviewRead])
async def list_reviews(
    seller_id: int, service: ShopServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list_reviews(seller_id, offset, limit)


@router.get("/customer/sellers/{seller_id}/review", response_model=ReviewEligibility)
async def review_eligibility(seller_id: int, account: CustomerAccount, service: ShopServiceDep):
    return await service.eligibility(account.customer_id, seller_id)


@router.put("/customer/sellers/{seller_id}/review", response_model=SellerReviewRead)
async def save_review(seller_id: int, data: SellerReviewWrite, account: CustomerAccount, service: ShopServiceDep):
    return await service.save_review(account.customer_id, seller_id, data)


@router.delete("/customer/sellers/{seller_id}/review", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(seller_id: int, account: CustomerAccount, service: ShopServiceDep):
    await service.delete_review(account.customer_id, seller_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
