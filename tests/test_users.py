from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.users import router
from app.core.db import Base
from app.exceptions import UserNotFound
from app.main import user_not_found_handler


@pytest.fixture
def client():
    @asynccontextmanager
    async def lifespan(app):
        engine = create_async_engine("sqlite+aiosqlite://")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            app.state.db = engine
            yield
        finally:
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    app.add_exception_handler(UserNotFound, user_not_found_handler)
    with TestClient(app) as client:
        yield client


def test_user_crud(client):
    assert client.get("/users").json() == []
    response = client.post("/users", json={"name": "Alice"})
    assert response.status_code == 201
    user = response.json()
    assert user["name"] == "Alice"
    url = f"/users/{user['id']}"
    assert client.get(url).json() == user
    assert client.get("/users").json() == [user]
    assert client.get("/users?offset=1&limit=1").json() == []
    response = client.put(url, json={"name": "Bob"})
    assert response.status_code == 200
    assert response.json() == {"id": user["id"], "name": "Bob"}
    assert client.get(url).json()["name"] == "Bob"
    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(url).status_code == 404
    assert client.get("/users").json() == []


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_user(client, method):
    kwargs = {"json": {"name": "Alice"}} if method == "put" else {}
    response = getattr(client, method)("/users/999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "User 999 not found"}


def test_validation(client):
    for data in ({}, {"name": ""}, {"name": "a" * 101}, {"name": None}):
        assert client.post("/users", json=data).status_code == 422
    assert client.get("/users?offset=-1").status_code == 422
    assert client.get("/users?limit=101").status_code == 422


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_failed_write_rolls_back(client, monkeypatch, method):
    user = client.post("/users", json={"name": "Alice"}).json()
    original_flush = AsyncSession.flush

    async def failing_flush(session, *args, **kwargs):
        await original_flush(session, *args, **kwargs)
        raise RuntimeError("Failure after database write")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "flush", failing_flush)
        url = "/users" if method == "post" else f"/users/{user['id']}"
        kwargs = {} if method == "delete" else {"json": {"name": "Bob"}}
        with pytest.raises(RuntimeError, match="Failure after database write"):
            getattr(client, method)(url, **kwargs)

    assert client.get("/users").json() == [user]
    assert client.post("/users", json={"name": "Charlie"}).status_code == 201
