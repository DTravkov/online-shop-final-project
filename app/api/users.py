from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.service.user import UserService, get_user_service

router = APIRouter(prefix="/users", tags=["users"])
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, service: UserServiceDep):
    return await service.create(data)


@router.get("", response_model=list[UserRead])
async def list_users(
    service: UserServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list(offset, limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, service: UserServiceDep):
    return await service.get(user_id)


@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, data: UserUpdate, service: UserServiceDep):
    return await service.update(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, service: UserServiceDep):
    await service.delete(user_id)
