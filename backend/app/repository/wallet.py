from decimal import Decimal
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.wallet_transaction import WalletTransaction


class WalletRepository:
    """Ledger writes participate in the account/order service transaction."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def history(self, account_id: int, offset: int, limit: int) -> list[WalletTransaction]:
        result = await self.db.scalars(
            select(WalletTransaction).where(WalletTransaction.account_id == account_id)
            .order_by(WalletTransaction.transaction_id.desc()).offset(offset).limit(limit)
        )
        return list(result.all())

    async def for_order(self, order_id: int) -> list[WalletTransaction]:
        result = await self.db.scalars(
            select(WalletTransaction).where(WalletTransaction.order_id == order_id)
            .order_by(WalletTransaction.transaction_id)
        )
        return list(result.all())

    async def create(self, account_id: int, amount: Decimal, kind: str, order_id: int | None = None) -> None:
        self.db.add(WalletTransaction(account_id=account_id, order_id=order_id, kind=kind, amount=amount))
        await self.db.flush()


def get_wallet_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> WalletRepository:
    return WalletRepository(db)
