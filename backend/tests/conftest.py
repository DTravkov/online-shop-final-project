"""API tests run against a real PostgreSQL database named by TEST_DATABASE_URL.

Example (from backend/):
    TEST_DATABASE_URL=postgresql://shop:shop@localhost:5432/shop_test python -m pytest

The database is wiped before every test. Tests that need it are skipped when the
variable is not set; schema-only tests always run.
"""

import asyncio
import os

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "admin-password"

if TEST_DATABASE_URL:
    # app.core.config reads these at import time, so set them before importing the app.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL
    os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD


async def _drop_all_tables() -> None:
    import app.models  # noqa: F401  Register every table.
    from app.core.db import Base, create_engine

    engine = create_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()


@pytest.fixture
def api():
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to run API tests against PostgreSQL.")
    from fastapi.testclient import TestClient

    from app.main import app

    asyncio.run(_drop_all_tables())
    with TestClient(app) as client:
        yield client


class Actor:
    """A signed-in account that sends requests with its bearer token."""

    def __init__(self, client, token_response: dict):
        self.client = client
        self.token = token_response["access_token"]
        self.account_id = token_response["account_id"]
        self.customer_id = token_response.get("customer_id")
        self.seller_id = token_response.get("seller_id")

    def _call(self, method: str, url: str, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}", **kwargs.pop("headers", {})}
        return self.client.request(method, url, headers=headers, **kwargs)

    def get(self, url, **kwargs):
        return self._call("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._call("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self._call("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self._call("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self._call("DELETE", url, **kwargs)


def register_customer(client, email="buyer@test.local", **overrides) -> Actor:
    payload = {
        "email": email,
        "password": "buyer-password",
        "full_name": "Aigerim Buyer",
        "phone": "+77010000000",
        "delivery_address": "Almaty, Abay 1",
        **overrides,
    }
    response = client.post("/auth/register/customer", json=payload)
    assert response.status_code == 201, response.text
    return Actor(client, response.json())


def register_seller(client, email="store@test.local", store_name="Store", **overrides) -> Actor:
    payload = {
        "email": email,
        "password": "seller-password",
        "store_name": store_name,
        "phone": "+77020000000",
        **overrides,
    }
    response = client.post("/auth/register/seller", json=payload)
    assert response.status_code == 201, response.text
    return Actor(client, response.json())


def login_admin(client) -> Actor:
    response = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert response.status_code == 200, response.text
    return Actor(client, response.json())


def add_product(seller: Actor, name="Phone", price="100.00", stock=10) -> dict:
    response = seller.post(
        "/seller/products", json={"product_name": name, "price": price, "stock_quantity": stock}
    )
    assert response.status_code == 201, response.text
    return response.json()
