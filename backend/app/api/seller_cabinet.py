from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.order import OrderStatus, OrderStatusUpdate, SellerOrderRead
from app.schemas.product import ProductRead, SellerProductCreate, SellerProductUpdate
from app.schemas.seller import SellerProfileUpdate, SellerRead
from app.service.auth import SellerAccount
from app.service.seller_order import SellerOrderService, get_seller_order_service
from app.service.seller_store import SellerStoreService, get_seller_store_service

router = APIRouter(prefix="/seller", tags=["seller cabinet"])
StoreServiceDep = Annotated[SellerStoreService, Depends(get_seller_store_service)]
OrderServiceDep = Annotated[SellerOrderService, Depends(get_seller_order_service)]


# --- Store profile ---------------------------------------------------------------

@router.get("/profile", response_model=SellerRead)
async def get_profile(account: SellerAccount, service: StoreServiceDep):
    """Store profile, including the current rating."""
    return await service.get_profile(account.seller_id)


@router.patch("/profile", response_model=SellerRead)
async def update_profile(data: SellerProfileUpdate, account: SellerAccount, service: StoreServiceDep):
    return await service.update_profile(account.seller_id, data)


# --- Products --------------------------------------------------------------------

@router.get("/products", response_model=list[ProductRead])
async def list_products(
    account: SellerAccount,
    service: StoreServiceDep,
    include_inactive: Annotated[bool, Query(description="Also list withdrawn products")] = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list_products(account.seller_id, include_inactive, offset, limit)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: SellerProductCreate, account: SellerAccount, service: StoreServiceDep):
    return await service.create_product(account.seller_id, data)


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, account: SellerAccount, service: StoreServiceDep):
    return await service.get_product(account.seller_id, product_id)


@router.patch("/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int, data: SellerProductUpdate, account: SellerAccount, service: StoreServiceDep
):
    """Change name, price, or stock. Send is_active=true to put a product back on sale."""
    return await service.update_product(account.seller_id, product_id, data)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_product(product_id: int, account: SellerAccount, service: StoreServiceDep):
    """Take a product off sale. It remains in order history."""
    await service.withdraw_product(account.seller_id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Orders ----------------------------------------------------------------------

@router.get("/orders", response_model=list[SellerOrderRead])
async def list_orders(
    account: SellerAccount,
    service: OrderServiceDep,
    order_status: OrderStatus | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Orders containing this seller's products, newest first."""
    return await service.list_orders(account.seller_id, order_status, offset, limit)


@router.get("/orders/{order_id}", response_model=SellerOrderRead)
async def get_order(order_id: int, account: SellerAccount, service: OrderServiceDep):
    return await service.get_order(account.seller_id, order_id)


@router.patch("/orders/{order_id}/status", response_model=SellerOrderRead)
async def update_order_status(
    order_id: int, data: OrderStatusUpdate, account: SellerAccount, service: OrderServiceDep
):
    """Allowed: new → shipped, new → delivered, shipped → delivered."""
    return await service.update_status(account.seller_id, order_id, data)
