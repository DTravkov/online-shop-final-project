import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with asyncpg.create_pool(os.environ["DATABASE_URL"]) as pool:
        async with Redis.from_url(os.environ["REDIS_URL"]) as redis:
            app.state.db = pool
            app.state.redis = redis
            yield


app = FastAPI(title="Online Shop API", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Online Shop API"}


@app.get("/health")
async def health():
    try:
        await app.state.db.fetchval("SELECT 1")
        await app.state.redis.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Service unavailable") from None
    return {"status": "ok", "postgres": "ok", "redis": "ok"}
