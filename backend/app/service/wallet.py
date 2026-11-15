from collections import defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import Depends

from app.exceptions import BusinessRuleViolation, RecordNotFound
from app.models.account import Account
from app.models.order import Order
from app.repository.account import AccountRepository, get_account_repository
from app.repository.order_item import OrderItemRepository, get_order_item_repository
from app.repository.wallet import WalletRepository, get_wallet_repository
from app.schemas.wallet import MAX_BALANCE, WalletDeposit, WalletRead, WalletTransactionRead


class WalletService:
    def __init__(self, accounts: AccountRepository, ledger: WalletRepository, items: OrderItemRepository):
        self.accounts = accounts
        self.ledger = ledger
        self.items = items

    async def get(self, account_id: int) -> WalletRead:
        account = await self.accounts.get(account_id)
        if account is None:
            raise RecordNotFound("Account", account_id)
        return WalletRead.model_validate(account)

    async def history(self, account_id: int, offset: int, limit: int) -> list[WalletTransactionRead]:
        await self.get(account_id)
        rows = await self.ledger.history(account_id, offset, limit)
        return [WalletTransactionRead.model_validate(row) for row in rows]

    async def deposit(self, account_id: int, data: WalletDeposit) -> WalletRead:
        async with self.accounts.transaction():
            accounts = await self.accounts.get_many_for_update([account_id])
            if not accounts:
                raise RecordNotFound("Account", account_id)
            account = accounts[0]
            await self._apply([(account, data.amount, "deposit")])
            return WalletRead.model_validate(account)

    async def _apply(self, movements: list[tuple[Account, Decimal, str]], order_id: int | None = None) -> None:
        # All accounts are already locked. Validate every balance before flushing any change.
        for account, amount, _kind in movements:
            balance = account.balance + amount
            if balance < 0:
                raise BusinessRuleViolation("Insufficient balance. Deposit funds before paying for this order.")
            if balance > MAX_BALANCE:
                raise BusinessRuleViolation("The resulting balance exceeds the maximum supported amount.")
        for account, amount, kind in movements:
            await self.accounts.update(account, {"balance": account.balance + amount})
            await self.ledger.create(account.account_id, amount, kind, order_id)

    async def charge_order(self, order: Order) -> None:
        """Called inside the caller's order transaction, after locking/creating the order."""
        if await self.ledger.for_order(order.order_id):
            raise BusinessRuleViolation("This order already has a balance payment.")
        payouts: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for item, _product, seller in await self.items.list_details([order.order_id]):
            payouts[seller.seller_id] += item.unit_price * item.quantity
        if not payouts or sum(payouts.values(), Decimal("0.00")) != order.total_amount:
            raise BusinessRuleViolation("Order items must match the order total before payment.")
        participants = await self.accounts.lock_payment_accounts(order.customer_id, list(payouts))
        buyer = next((account for account in participants if account.customer_id == order.customer_id), None)
        sellers = {account.seller_id: account for account in participants if account.role == "seller"}
        if buyer is None or buyer.role != "customer":
            raise BusinessRuleViolation("The buyer needs an account with a balance.")
        if any(seller_id not in sellers for seller_id in payouts):
            raise BusinessRuleViolation("Every seller needs an account to receive payment.")
        movements = [(buyer, -order.total_amount, "payment")]
        movements.extend((sellers[seller_id], amount, "sale") for seller_id, amount in sorted(payouts.items()))
        await self._apply(movements, order.order_id)

    async def refund_order(self, order: Order) -> None:
        """Reverse original ledger amounts, even if listings or order items have changed."""
        entries = await self.ledger.for_order(order.order_id)
        if any(entry.kind == "refund" for entry in entries):
            raise BusinessRuleViolation("This order has already been refunded to a balance.")
        originals = [entry for entry in entries if entry.kind in {"payment", "sale"}]
        if not any(entry.kind == "payment" for entry in originals):
            raise BusinessRuleViolation("This order has no balance payment to refund.")
        accounts = {
            account.account_id: account
            for account in await self.accounts.get_many_for_update([entry.account_id for entry in originals])
        }
        movements = [
            (accounts[entry.account_id], -entry.amount, "refund" if entry.kind == "payment" else "sale_refund")
            for entry in originals
        ]
        await self._apply(movements, order.order_id)


def get_wallet_service(
    accounts: Annotated[AccountRepository, Depends(get_account_repository)],
    ledger: Annotated[WalletRepository, Depends(get_wallet_repository)],
    items: Annotated[OrderItemRepository, Depends(get_order_item_repository)],
) -> WalletService:
    return WalletService(accounts, ledger, items)
