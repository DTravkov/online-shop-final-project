from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate
from app.service.order_item import OrderItemService, get_order_item_service

router = APIRouter(prefix="/order-items", tags=["order-items"])
OrderItemServiceDep = Annotated[OrderItemService, Depends(get_order_item_service)]


@router.post("", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED)
async def create_order_item(data: OrderItemCreate, service: OrderItemServiceDep):
    return await service.create(data)


@router.get("", response_model=list[OrderItemRead])
async def list_records(
    service: OrderItemServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list(offset, limit)


@router.get("/{order_item_id}", response_model=OrderItemRead)
async def get_order_item(order_item_id: int, service: OrderItemServiceDep):
    return await service.get(order_item_id)


@router.put("/{order_item_id}", response_model=OrderItemRead)
async def update_order_item(order_item_id: int, data: OrderItemUpdate, service: OrderItemServiceDep):
    return await service.update(order_item_id, data)


@router.delete("/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_item(order_item_id: int, service: OrderItemServiceDep):
    await service.delete(order_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
