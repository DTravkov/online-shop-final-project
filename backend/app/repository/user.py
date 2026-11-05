from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def transaction(self):
        return self.db.begin()

    async def list(self, offset: int, limit: int):
        result = await self.db.scalars(select(User).order_by(User.id).offset(offset).limit(limit))
        return result.all()

    async def get(self, user_id: int):
        return await self.db.get(User, user_id)

    async def create(self, name: str):
        user = User(name=name)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, name: str):
        user.name = name
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User):
        await self.db.delete(user)
        await self.db.flush()


def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)
