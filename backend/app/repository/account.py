from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.account import Account


class AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Account conflicts with existing records.") from exc

    async def get(self, account_id: int) -> Account | None:
        return await self.db.get(Account, account_id)

    async def get_by_email(self, email: str) -> Account | None:
        return await self.db.scalar(select(Account).where(Account.email == email))

    async def get_by_customer_id(self, customer_id: int) -> Account | None:
        return await self.db.scalar(select(Account).where(Account.customer_id == customer_id))

    async def get_by_seller_id(self, seller_id: int) -> Account | None:
        return await self.db.scalar(select(Account).where(Account.seller_id == seller_id))

    async def create(self, values: dict[str, Any]) -> Account:
        record = Account(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: Account, values: dict[str, Any]) -> Account:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record


def get_account_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> AccountRepository:
    return AccountRepository(db)
