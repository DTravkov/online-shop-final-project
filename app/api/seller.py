from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.seller import SellerCreate, SellerRead, SellerUpdate
from app.service.seller import SellerService, get_seller_service

router = APIRouter(prefix="/sellers", tags=["sellers"])
SellerServiceDep = Annotated[SellerService, Depends(get_seller_service)]


@router.post("", response_model=SellerRead, status_code=status.HTTP_201_CREATED)
async def create_seller(data: SellerCreate, service: SellerServiceDep):
    return await service.create(data)


@router.get("", response_model=list[SellerRead])
async def list_records(
    service: SellerServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list(offset, limit)


@router.get("/{seller_id}", response_model=SellerRead)
async def get_seller(seller_id: int, service: SellerServiceDep):
    return await service.get(seller_id)


@router.put("/{seller_id}", response_model=SellerRead)
async def update_seller(seller_id: int, data: SellerUpdate, service: SellerServiceDep):
    return await service.update(seller_id, data)


@router.delete("/{seller_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seller(seller_id: int, service: SellerServiceDep):
    await service.delete(seller_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
