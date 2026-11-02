from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.repository.order import OrderRepository, get_order_repository
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate


class OrderService:
    def __init__(self, repository: OrderRepository):
        self.repository = repository

    async def list(self, offset: int, limit: int) -> list[OrderRead]:
        records = await self.repository.list(offset, limit)
        return [OrderRead.model_validate(record) for record in records]

    async def _get_record(self, order_id: int):
        record = await self.repository.get(order_id)
        if record is None:
            raise RecordNotFound("Order", order_id)
        return record

    async def get(self, order_id: int) -> OrderRead:
        return OrderRead.model_validate(await self._get_record(order_id))

    async def create(self, data: OrderCreate) -> OrderRead:
        async with self.repository.transaction():
            record = await self.repository.create(data.model_dump())
            return OrderRead.model_validate(record)

    async def update(self, order_id: int, data: OrderUpdate) -> OrderRead:
        async with self.repository.transaction():
            record = await self._get_record(order_id)
            record = await self.repository.update(record, data.model_dump())
            return OrderRead.model_validate(record)

    async def delete(self, order_id: int) -> None:
        async with self.repository.transaction():
            await self.repository.delete(await self._get_record(order_id))


def get_order_service(
    repository: Annotated[OrderRepository, Depends(get_order_repository)],
) -> OrderService:
    return OrderService(repository)
