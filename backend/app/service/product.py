from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.repository.product import ProductRepository, get_product_repository
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate


class ProductService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    async def list(self, offset: int, limit: int) -> list[ProductRead]:
        records = await self.repository.list(offset, limit)
        return [ProductRead.model_validate(record) for record in records]

    async def _get_record(self, product_id: int):
        record = await self.repository.get(product_id)
        if record is None:
            raise RecordNotFound("Product", product_id)
        return record

    async def get(self, product_id: int) -> ProductRead:
        return ProductRead.model_validate(await self._get_record(product_id))

    async def create(self, data: ProductCreate) -> ProductRead:
        async with self.repository.transaction():
            record = await self.repository.create(data.model_dump())
            return ProductRead.model_validate(record)

    async def update(self, product_id: int, data: ProductUpdate) -> ProductRead:
        async with self.repository.transaction():
            record = await self._get_record(product_id)
            record = await self.repository.update(record, data.model_dump())
            return ProductRead.model_validate(record)

    async def delete(self, product_id: int) -> None:
        async with self.repository.transaction():
            await self.repository.delete(await self._get_record(product_id))


def get_product_service(
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductService:
    return ProductService(repository)
