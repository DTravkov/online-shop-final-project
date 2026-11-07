from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.schemas.auth import AccountRead, CustomerRegister, LoginRequest, SellerRegister, TokenResponse
from app.service.auth import AuthenticatedAccount, AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register/customer", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(data: CustomerRegister, service: AuthServiceDep):
    return await service.register_customer(data)


@router.post("/register/seller", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_seller(data: SellerRegister, service: AuthServiceDep):
    return await service.register_seller(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: AuthServiceDep):
    return await service.login(data)


@router.get("/me", response_model=AccountRead)
async def get_me(account: AuthenticatedAccount, service: AuthServiceDep):
    return await service.get_account(account.account_id)
