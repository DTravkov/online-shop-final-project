from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

import app.models  # Register all tables with Base.metadata.
from app.api.customer import router as customers_router
from app.api.order import router as orders_router
from app.api.order_item import router as order_items_router
from app.api.product import router as products_router
from app.api.seller import router as sellers_router
from app.api.users import router as users_router
from app.core.config import DATABASE_URL, REDIS_URL
from app.core.db import Base, create_engine
from app.exceptions import RecordConflict, RecordNotFound, UserNotFound


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with Redis.from_url(REDIS_URL) as redis:
            app.state.db = engine
            app.state.redis = redis
            yield
    finally:
        await engine.dispose()


app = FastAPI(title="Online Shop API", lifespan=lifespan)
app.include_router(users_router)
app.include_router(customers_router)
app.include_router(sellers_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(order_items_router)


@app.exception_handler(RecordNotFound)
async def record_not_found_handler(request: Request, exc: RecordNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(RecordConflict)
async def record_conflict_handler(request: Request, exc: RecordConflict):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(UserNotFound)
async def user_not_found_handler(request: Request, exc: UserNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/")
async def root():
    return {"message": "Online Shop API"}


@app.get("/health")
async def health(request: Request):
    try:
        async with request.app.state.db.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await request.app.state.redis.ping()
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Service unavailable"})
    return {"status": "ok", "postgres": "ok", "redis": "ok"}
