from typing import Annotated

from fastapi import Depends

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.exceptions import UserNotFound
from app.repository.user import UserRepository, get_user_repository


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def list(self, offset: int, limit: int) -> list[UserRead]:
        return [UserRead.model_validate(user) for user in await self.repository.list(offset, limit)]

    async def _get_user(self, user_id: int):
        user = await self.repository.get(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    async def get(self, user_id: int) -> UserRead:
        return UserRead.model_validate(await self._get_user(user_id))

    async def create(self, data: UserCreate) -> UserRead:
        async with self.repository.transaction():
            return UserRead.model_validate(await self.repository.create(data.name))

    async def update(self, user_id: int, data: UserUpdate) -> UserRead:
        async with self.repository.transaction():
            user = await self._get_user(user_id)
            return UserRead.model_validate(await self.repository.update(user, data.name))

    async def delete(self, user_id: int) -> None:
        async with self.repository.transaction():
            await self.repository.delete(await self._get_user(user_id))


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository)
