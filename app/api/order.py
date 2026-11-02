from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.order import OrderCreate, OrderRead, OrderUpdate
from app.service.order import OrderService, get_order_service

router = APIRouter(prefix="/orders", tags=["orders"])
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, service: OrderServiceDep):
    return await service.create(data)


@router.get("", response_model=list[OrderRead])
async def list_records(
    service: OrderServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list(offset, limit)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, service: OrderServiceDep):
    return await service.get(order_id)


@router.put("/{order_id}", response_model=OrderRead)
async def update_order(order_id: int, data: OrderUpdate, service: OrderServiceDep):
    return await service.update(order_id, data)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: int, service: OrderServiceDep):
    await service.delete(order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
