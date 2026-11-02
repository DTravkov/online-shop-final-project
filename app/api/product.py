from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.service.product import ProductService, get_product_service

router = APIRouter(prefix="/products", tags=["products"])
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, service: ProductServiceDep):
    return await service.create(data)


@router.get("", response_model=list[ProductRead])
async def list_records(
    service: ProductServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list(offset, limit)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, service: ProductServiceDep):
    return await service.get(product_id)


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, data: ProductUpdate, service: ProductServiceDep):
    return await service.update(product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, service: ProductServiceDep):
    await service.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
