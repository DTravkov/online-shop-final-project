from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.repository.seller import SellerRepository, get_seller_repository
from app.schemas.seller import SellerCreate, SellerRead, SellerUpdate


class SellerService:
    def __init__(self, repository: SellerRepository):
        self.repository = repository

    async def list(self, offset: int, limit: int) -> list[SellerRead]:
        records = await self.repository.list(offset, limit)
        return [SellerRead.model_validate(record) for record in records]

    async def _get_record(self, seller_id: int):
        record = await self.repository.get(seller_id)
        if record is None:
            raise RecordNotFound("Seller", seller_id)
        return record

    async def get(self, seller_id: int) -> SellerRead:
        return SellerRead.model_validate(await self._get_record(seller_id))

    async def create(self, data: SellerCreate) -> SellerRead:
        async with self.repository.transaction():
            record = await self.repository.create(data.model_dump())
            return SellerRead.model_validate(record)

    async def update(self, seller_id: int, data: SellerUpdate) -> SellerRead:
        async with self.repository.transaction():
            record = await self._get_record(seller_id)
            record = await self.repository.update(record, data.model_dump())
            return SellerRead.model_validate(record)

    async def delete(self, seller_id: int) -> None:
        async with self.repository.transaction():
            await self.repository.delete(await self._get_record(seller_id))


def get_seller_service(
    repository: Annotated[SellerRepository, Depends(get_seller_repository)],
) -> SellerService:
    return SellerService(repository)
