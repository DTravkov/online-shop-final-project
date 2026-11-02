from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.repository.customer import CustomerRepository, get_customer_repository
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate


class CustomerService:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    async def list(self, offset: int, limit: int) -> list[CustomerRead]:
        records = await self.repository.list(offset, limit)
        return [CustomerRead.model_validate(record) for record in records]

    async def _get_record(self, customer_id: int):
        record = await self.repository.get(customer_id)
        if record is None:
            raise RecordNotFound("Customer", customer_id)
        return record

    async def get(self, customer_id: int) -> CustomerRead:
        return CustomerRead.model_validate(await self._get_record(customer_id))

    async def create(self, data: CustomerCreate) -> CustomerRead:
        async with self.repository.transaction():
            record = await self.repository.create(data.model_dump())
            return CustomerRead.model_validate(record)

    async def update(self, customer_id: int, data: CustomerUpdate) -> CustomerRead:
        async with self.repository.transaction():
            record = await self._get_record(customer_id)
            record = await self.repository.update(record, data.model_dump())
            return CustomerRead.model_validate(record)

    async def delete(self, customer_id: int) -> None:
        async with self.repository.transaction():
            await self.repository.delete(await self._get_record(customer_id))


def get_customer_service(
    repository: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> CustomerService:
    return CustomerService(repository)
