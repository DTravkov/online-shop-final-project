import asyncio
from decimal import Decimal
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.exceptions import (
    AuthenticationFailed,
    PermissionDenied,
    RecordConflict,
    RecordNotFound,
)
from app.models.account import Account
from app.repository.account import AccountRepository, get_account_repository
from app.repository.customer import CustomerRepository, get_customer_repository
from app.repository.seller import SellerRepository, get_seller_repository
from app.schemas.auth import (
    AccountRead,
    CurrentAccount,
    CustomerRegister,
    LoginRequest,
    SellerRegister,
    TokenResponse,
)
from app.utils.email import normalize_email

NEW_SELLER_RATING = Decimal("0.0")


def issue_token(account: Account) -> TokenResponse:
    claims = {
        "sub": str(account.account_id),
        "role": account.role,
        "customer_id": account.customer_id,
        "seller_id": account.seller_id,
    }
    return TokenResponse(
        access_token=create_access_token(claims),
        account_id=account.account_id,
        role=account.role,
        customer_id=account.customer_id,
        seller_id=account.seller_id,
    )


async def change_account_email(
    accounts: AccountRepository, account: Account | None, email: str
) -> None:
    """Keep the login email in sync with a profile email. Call inside a transaction."""
    if account is None or account.email == email:
        return
    owner = await accounts.get_by_email(email)
    if owner is not None and owner.account_id != account.account_id:
        raise RecordConflict("Email is already registered.")
    await accounts.update(account, {"email": email})


class AuthService:
    def __init__(
        self,
        accounts: AccountRepository,
        customers: CustomerRepository,
        sellers: SellerRepository,
    ):
        self.accounts = accounts
        self.customers = customers
        self.sellers = sellers

    async def register_customer(self, data: CustomerRegister) -> TokenResponse:
        password_hash = await asyncio.to_thread(hash_password, data.password)
        async with self.accounts.transaction():
            await self._ensure_email_free(data.email)
            customer = await self.customers.create(
                data.model_dump(include={"full_name", "email", "phone", "delivery_address"})
            )
            account = await self.accounts.create({
                "email": data.email,
                "password_hash": password_hash,
                "role": "customer",
                "customer_id": customer.customer_id,
            })
            return issue_token(account)

    async def register_seller(self, data: SellerRegister) -> TokenResponse:
        password_hash = await asyncio.to_thread(hash_password, data.password)
        async with self.accounts.transaction():
            await self._ensure_email_free(data.email)
            seller = await self.sellers.create({
                **data.model_dump(include={"store_name", "email", "phone"}),
                "rating": NEW_SELLER_RATING,
            })
            account = await self.accounts.create({
                "email": data.email,
                "password_hash": password_hash,
                "role": "seller",
                "seller_id": seller.seller_id,
            })
            return issue_token(account)

    async def login(self, data: LoginRequest) -> TokenResponse:
        account = await self.accounts.get_by_email(data.email)
        password_hash = account.password_hash if account is not None else DUMMY_PASSWORD_HASH
        valid = await asyncio.to_thread(verify_password, data.password, password_hash)
        if account is None or not valid:
            raise AuthenticationFailed("Incorrect email or password.")
        return issue_token(account)

    async def get_account(self, account_id: int) -> AccountRead:
        account = await self.accounts.get(account_id)
        if account is None:
            raise RecordNotFound("Account", account_id)
        return AccountRead.model_validate(account)

    async def _ensure_email_free(self, email: str) -> None:
        if await self.accounts.get_by_email(email) is not None:
            raise RecordConflict("Email is already registered.")


def get_auth_service(
    accounts: Annotated[AccountRepository, Depends(get_account_repository)],
    customers: Annotated[CustomerRepository, Depends(get_customer_repository)],
    sellers: Annotated[SellerRepository, Depends(get_seller_repository)],
) -> AuthService:
    return AuthService(accounts, customers, sellers)


async def ensure_admin_account(engine: AsyncEngine, email: str, password: str) -> None:
    """Create the configured administrator on startup if no account uses that email."""
    email = normalize_email(email)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        accounts = AccountRepository(session)
        if await accounts.get_by_email(email) is not None:
            return
        await session.rollback()
        password_hash = await asyncio.to_thread(hash_password, password)
        try:
            async with accounts.transaction():
                await accounts.create({"email": email, "password_hash": password_hash, "role": "admin"})
        except RecordConflict:
            pass  # Another worker created it first.


# --- Authentication dependencies -------------------------------------------------
#
# Tokens are verified without a database query, so a request's session has no open
# transaction when a service starts its own write transaction.

bearer_scheme = HTTPBearer(auto_error=False, description="Access token from /auth/login")


async def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentAccount:
    if credentials is None:
        raise AuthenticationFailed("Not authenticated.")
    try:
        payload = decode_access_token(credentials.credentials)
        return CurrentAccount(
            account_id=int(payload["sub"]),
            role=payload["role"],
            customer_id=payload.get("customer_id"),
            seller_id=payload.get("seller_id"),
        )
    except (jwt.PyJWTError, KeyError, ValueError, ValidationError) as exc:
        raise AuthenticationFailed("Invalid or expired token.") from exc


async def require_customer(
    account: Annotated[CurrentAccount, Depends(get_current_account)],
) -> CurrentAccount:
    if account.role != "customer" or account.customer_id is None:
        raise PermissionDenied("A customer account is required.")
    return account


async def require_seller(
    account: Annotated[CurrentAccount, Depends(get_current_account)],
) -> CurrentAccount:
    if account.role != "seller" or account.seller_id is None:
        raise PermissionDenied("A seller account is required.")
    return account


async def require_admin(
    account: Annotated[CurrentAccount, Depends(get_current_account)],
) -> CurrentAccount:
    if account.role != "admin":
        raise PermissionDenied("An administrator account is required.")
    return account


AuthenticatedAccount = Annotated[CurrentAccount, Depends(get_current_account)]
CustomerAccount = Annotated[CurrentAccount, Depends(require_customer)]
SellerAccount = Annotated[CurrentAccount, Depends(require_seller)]
AdminAccount = Annotated[CurrentAccount, Depends(require_admin)]
