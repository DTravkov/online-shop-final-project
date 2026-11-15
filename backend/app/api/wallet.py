from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.schemas.wallet import WalletDeposit, WalletRead, WalletTransactionRead
from app.service.auth import AuthenticatedAccount
from app.service.wallet import WalletService, get_wallet_service

router = APIRouter(prefix="/wallet", tags=["wallet"])
WalletServiceDep = Annotated[WalletService, Depends(get_wallet_service)]


@router.get("", response_model=WalletRead)
async def get_wallet(account: AuthenticatedAccount, service: WalletServiceDep):
    return await service.get(account.account_id)


@router.post("/deposit", response_model=WalletRead)
async def deposit(data: WalletDeposit, account: AuthenticatedAccount, service: WalletServiceDep):
    """Testing top-up: adds funds without contacting an external payment provider."""
    return await service.deposit(account.account_id, data)


@router.get("/transactions", response_model=list[WalletTransactionRead])
async def list_transactions(
    account: AuthenticatedAccount, service: WalletServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.history(account.account_id, offset, limit)
