import asyncio
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.security import hash_password
from app.exceptions import RecordConflict
from app.repository.account import AccountRepository
from app.repository.customer import CustomerRepository
from app.repository.product import ProductRepository
from app.repository.seller import SellerRepository

DEMO_CUSTOMER = {
    "full_name": "test",
    "email": "test@gmail.com",
    "phone": "+77010000001",
    "delivery_address": "Almaty, Abay 1",
}
DEMO_CUSTOMER_PASSWORD = "test"

DEMO_SELLER = {
    "store_name": "test1",
    "email": "test1@gmail.com",
    "phone": "+77010000002",
    "rating": Decimal("0.0"),
}
DEMO_SELLER_PASSWORD = "test1..."

DEMO_PRODUCTS = [
    {"product_name": "Apple iPhone 15 128GB Black", "price": Decimal("429990.00"), "stock_quantity": 15},
    {"product_name": "Samsung Galaxy Buds2 Pro Graphite", "price": Decimal("69990.00"), "stock_quantity": 40},
]


async def ensure_demo_data(engine: AsyncEngine) -> None:
    """Create the demo customer, seller, and products on startup if their emails are free.

    Records are written directly, so the demo passwords skip registration validation.
    """
    await _ensure_demo_customer(engine)
    await _ensure_demo_seller(engine)


async def _ensure_demo_customer(engine: AsyncEngine) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        accounts = AccountRepository(session)
        if await accounts.get_by_email(DEMO_CUSTOMER["email"]) is not None:
            return
        await session.rollback()
        password_hash = await asyncio.to_thread(hash_password, DEMO_CUSTOMER_PASSWORD)
        try:
            async with accounts.transaction():
                customer = await CustomerRepository(session).create(DEMO_CUSTOMER)
                await accounts.create({
                    "email": DEMO_CUSTOMER["email"],
                    "password_hash": password_hash,
                    "role": "customer",
                    "customer_id": customer.customer_id,
                })
        except RecordConflict:
            pass  # Another worker created it first.


async def _ensure_demo_seller(engine: AsyncEngine) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        accounts = AccountRepository(session)
        if await accounts.get_by_email(DEMO_SELLER["email"]) is not None:
            return
        await session.rollback()
        password_hash = await asyncio.to_thread(hash_password, DEMO_SELLER_PASSWORD)
        try:
            async with accounts.transaction():
                seller = await SellerRepository(session).create(DEMO_SELLER)
                await accounts.create({
                    "email": DEMO_SELLER["email"],
                    "password_hash": password_hash,
                    "role": "seller",
                    "seller_id": seller.seller_id,
                })
                products = ProductRepository(session)
                for product in DEMO_PRODUCTS:
                    await products.create({**product, "seller_id": seller.seller_id})
        except RecordConflict:
            pass  # Another worker created it first.
