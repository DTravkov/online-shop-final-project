from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.repository.order_item import OrderItemRepository, get_order_item_repository
from app.schemas.order_item import OrderItemCreate, OrderItemRead, OrderItemUpdate


class OrderItemService:
    def __init__(self, repository: OrderItemRepository):
        self.repository = repository

    async def list(self, offset: int, limit: int) -> list[OrderItemRead]:
        records = await self.repository.list(offset, limit)
        return [OrderItemRead.model_validate(record) for record in records]

    async def _get_record(self, order_item_id: int):
        record = await self.repository.get(order_item_id)
        if record is None:
            raise RecordNotFound("Order item", order_item_id)
        return record

    async def get(self, order_item_id: int) -> OrderItemRead:
        return OrderItemRead.model_validate(await self._get_record(order_item_id))

    async def create(self, data: OrderItemCreate) -> OrderItemRead:
        async with self.repository.transaction():
            record = await self.repository.create(data.model_dump())
            return OrderItemRead.model_validate(record)

    async def update(self, order_item_id: int, data: OrderItemUpdate) -> OrderItemRead:
        async with self.repository.transaction():
            record = await self._get_record(order_item_id)
            record = await self.repository.update(record, data.model_dump())
            return OrderItemRead.model_validate(record)

    async def delete(self, order_item_id: int) -> None:
        async with self.repository.transaction():
            await self.repository.delete(await self._get_record(order_item_id))


def get_order_item_service(
    repository: Annotated[OrderItemRepository, Depends(get_order_item_repository)],
) -> OrderItemService:
    return OrderItemService(repository)
