from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

import app.models  # Register all tables with Base.metadata.
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.customer import router as customers_router
from app.api.customer_cabinet import router as customer_cabinet_router
from app.api.order import router as orders_router
from app.api.order_item import router as order_items_router
from app.api.product import router as products_router
from app.api.seller import router as sellers_router
from app.api.seller_cabinet import router as seller_cabinet_router
from app.api.users import router as users_router
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD, DATABASE_URL, REDIS_URL
from app.core.db import Base, create_engine
from app.exceptions import (
    AuthenticationFailed,
    BusinessRuleViolation,
    PermissionDenied,
    RecordConflict,
    RecordNotFound,
    UserNotFound,
)
from app.service.auth import ensure_admin_account, require_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        if ADMIN_EMAIL and ADMIN_PASSWORD:
            await ensure_admin_account(engine, ADMIN_EMAIL, ADMIN_PASSWORD)
        async with Redis.from_url(REDIS_URL) as redis:
            app.state.db = engine
            app.state.redis = redis
            yield
    finally:
        await engine.dispose()


app = FastAPI(title="Online Shop API", lifespan=lifespan)

# Marketplace features.
app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(customer_cabinet_router)
app.include_router(seller_cabinet_router)
app.include_router(admin_router)

# Raw table CRUD bypasses the business rules, so only administrators may use it.
admin_only = [Depends(require_admin)]
app.include_router(customers_router, dependencies=admin_only)
app.include_router(sellers_router, dependencies=admin_only)
app.include_router(products_router, dependencies=admin_only)
app.include_router(orders_router, dependencies=admin_only)
app.include_router(order_items_router, dependencies=admin_only)

app.include_router(users_router)


@app.exception_handler(RecordNotFound)
async def record_not_found_handler(request: Request, exc: RecordNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(RecordConflict)
async def record_conflict_handler(request: Request, exc: RecordConflict):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(UserNotFound)
async def user_not_found_handler(request: Request, exc: UserNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(AuthenticationFailed)
async def authentication_failed_handler(request: Request, exc: AuthenticationFailed):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(PermissionDenied)
async def permission_denied_handler(request: Request, exc: PermissionDenied):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleViolation)
async def business_rule_violation_handler(request: Request, exc: BusinessRuleViolation):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


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
