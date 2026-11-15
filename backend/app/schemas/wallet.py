from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_BALANCE = Decimal("999999999999.99")
TransactionKind = Literal["deposit", "payment", "sale", "refund", "sale_refund"]


class WalletDeposit(BaseModel):
    amount: Decimal = Field(gt=0, le=MAX_BALANCE, max_digits=14, decimal_places=2)


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    balance: Decimal
    currency: Literal["KZT"] = "KZT"


class WalletTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: int
    order_id: int | None
    kind: TransactionKind
    amount: Decimal
    created_at: datetime
