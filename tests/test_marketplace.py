from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.db import Base
from app.main import app


RESOURCES = {
    "customers": ("customer_id", {"full_name": "Updated Customer"}),
    "sellers": ("seller_id", {"store_name": "Updated Shop", "rating": "4.8"}),
    "products": ("product_id", {"product_name": "Updated Product", "price": "15.25"}),
    "orders": ("order_id", {"order_status": "shipped", "total_amount": "30.50"}),
    "order-items": ("order_item_id", {"quantity": 3, "unit_price": "15.25"}),
}


@pytest.fixture
def client(monkeypatch):
    @asynccontextmanager
    async def lifespan(application):
        engine = create_async_engine("sqlite+aiosqlite://")

        @event.listens_for(engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            application.state.db = engine
            yield
        finally:
            await engine.dispose()

    monkeypatch.setattr(app.router, "lifespan_context", lifespan)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def records(client):
    """Create a valid chain of related records through the production routes."""
    payloads = {
        "customers": {
            "full_name": "Alice", "email": "alice@example.com",
            "phone": "123456789", "delivery_address": "1 Main Street",
        },
        "sellers": {
            "store_name": "Shop", "email": "shop@example.com",
            "phone": "987654321", "rating": "4.5",
        },
        "products": {
            "product_name": "Book", "price": "10.50", "stock_quantity": 20,
        },
        "orders": {
            "order_date": "2026-11-03T12:00:00", "total_amount": "21.00",
            "order_status": "new", "payment_status": "pending",
        },
        "order-items": {"quantity": 2, "unit_price": "10.50"},
    }
    result = {}
    for resource, payload in payloads.items():
        if resource == "products":
            payload["seller_id"] = result["sellers"]["seller_id"]
        elif resource == "orders":
            payload["customer_id"] = result["customers"]["customer_id"]
        elif resource == "order-items":
            payload["order_id"] = result["orders"]["order_id"]
            payload["product_id"] = result["products"]["product_id"]
        response = client.post(f"/{resource}", json=payload)
        assert response.status_code == 201, response.text
        result[resource] = response.json()
    return result


def payload_for(resource, records):
    pk, _ = RESOURCES[resource]
    return {key: value for key, value in records[resource].items() if key != pk}


@pytest.mark.parametrize("resource", RESOURCES)
def test_crud(client, records, resource):
    pk, changes = RESOURCES[resource]
    path = f"/{resource}"
    payload = payload_for(resource, records)
    before = client.get(path).json()
    response = client.post(path, json=payload)
    assert response.status_code == 201
    created = response.json()
    assert {key: value for key, value in created.items() if key != pk} == payload
    url = f"{path}/{created[pk]}"
    assert client.get(url).json() == created
    assert client.get(path).json() == before + [created]
    assert client.get(f"{path}?offset={len(before)}&limit=1").json() == [created]

    payload.update(changes)
    response = client.put(url, json=payload)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated == {**payload, pk: created[pk]}
    assert client.get(url).json() == updated

    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(url).status_code == 404
    assert client.get(path).json() == before


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_record(client, records, resource, method):
    kwargs = {"json": payload_for(resource, records)} if method == "put" else {}
    response = getattr(client, method)(f"/{resource}/99999", **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"].endswith("99999 not found")


@pytest.mark.parametrize("resource,field", [
    ("products", "seller_id"), ("orders", "customer_id"),
    ("order-items", "order_id"), ("order-items", "product_id"),
])
@pytest.mark.parametrize("method", ["post", "put"])
def test_invalid_reference_rolls_back(client, records, resource, field, method):
    pk, _ = RESOURCES[resource]
    path = f"/{resource}"
    before = client.get(path).json()
    payload = payload_for(resource, records)
    payload[field] = 99999
    url = path if method == "post" else f"{path}/{records[resource][pk]}"
    response = getattr(client, method)(url, json=payload)
    assert response.status_code == 409
    assert client.get(path).json() == before
    assert client.post(path, json=payload_for(resource, records)).status_code == 201


@pytest.mark.parametrize("resource", ["customers", "sellers", "products", "orders"])
def test_referenced_record_cannot_be_deleted(client, records, resource):
    pk, _ = RESOURCES[resource]
    url = f"/{resource}/{records[resource][pk]}"
    assert client.delete(url).status_code == 409
    assert client.get(url).json() == records[resource]


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_failure_after_flush_rolls_back(client, records, monkeypatch, resource, method):
    pk, changes = RESOURCES[resource]
    path = f"/{resource}"
    payload = payload_for(resource, records)
    created = client.post(path, json=payload).json()
    before = client.get(path).json()
    original_flush = AsyncSession.flush

    async def failing_flush(session, *args, **kwargs):
        await original_flush(session, *args, **kwargs)
        raise RuntimeError("Failure after database write")

    payload.update(changes)
    url = path if method == "post" else f"{path}/{created[pk]}"
    kwargs = {} if method == "delete" else {"json": payload}
    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", failing_flush)
        with pytest.raises(RuntimeError, match="Failure after database write"):
            getattr(client, method)(url, **kwargs)
    assert client.get(path).json() == before
    assert client.post(path, json=payload).status_code == 201


@pytest.mark.parametrize("resource", RESOURCES)
def test_validation(client, records, resource):
    pk, _ = RESOURCES[resource]
    path = f"/{resource}"
    assert client.post(path, json={}).status_code == 422
    assert client.put(f"{path}/{records[resource][pk]}", json={}).status_code == 422
    assert client.get(f"{path}?offset=-1").status_code == 422
    assert client.get(f"{path}?limit=101").status_code == 422


def test_crud_does_not_apply_checkout_rules(client, records):
    product = records["products"]
    order = records["orders"]
    item = records["order-items"]
    payload = payload_for("order-items", records)
    payload["quantity"] = 10
    assert client.put(f"/order-items/{item['order_item_id']}", json=payload).status_code == 200
    assert client.get(f"/products/{product['product_id']}").json() == product
    assert client.get(f"/orders/{order['order_id']}").json() == order


def test_related_records_can_be_deleted_in_dependency_order(client, records):
    for resource in ["order-items", "orders", "products", "customers", "sellers"]:
        pk, _ = RESOURCES[resource]
        assert client.delete(f"/{resource}/{records[resource][pk]}").status_code == 204
