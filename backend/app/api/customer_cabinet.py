from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.cart import CartItemAdd, CartItemQuantity, CartRead
from app.schemas.customer import CustomerProfileUpdate, CustomerRead, DeliveryAddress
from app.schemas.order import CheckoutRequest, OrderDetail, OrderStatus
from app.service.auth import CustomerAccount
from app.service.cart import CartService, get_cart_service
from app.service.customer_order import CustomerOrderService, get_customer_order_service
from app.service.customer_profile import CustomerProfileService, get_customer_profile_service

router = APIRouter(prefix="/customer", tags=["customer cabinet"])
ProfileServiceDep = Annotated[CustomerProfileService, Depends(get_customer_profile_service)]
CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
OrderServiceDep = Annotated[CustomerOrderService, Depends(get_customer_order_service)]


# --- Profile ---------------------------------------------------------------------

@router.get("/profile", response_model=CustomerRead)
async def get_profile(account: CustomerAccount, service: ProfileServiceDep):
    return await service.get(account.customer_id)


@router.patch("/profile", response_model=CustomerRead)
async def update_profile(data: CustomerProfileUpdate, account: CustomerAccount, service: ProfileServiceDep):
    return await service.update(account.customer_id, data)


@router.get("/delivery-address", response_model=DeliveryAddress)
async def get_delivery_address(account: CustomerAccount, service: ProfileServiceDep):
    return await service.get_delivery_address(account.customer_id)


@router.put("/delivery-address", response_model=DeliveryAddress)
async def set_delivery_address(data: DeliveryAddress, account: CustomerAccount, service: ProfileServiceDep):
    return await service.set_delivery_address(account.customer_id, data)


# --- Cart ------------------------------------------------------------------------

@router.get("/cart", response_model=CartRead)
async def get_cart(account: CustomerAccount, service: CartServiceDep):
    return await service.get_cart(account.customer_id)


@router.post("/cart/items", response_model=CartRead)
async def add_cart_item(data: CartItemAdd, account: CustomerAccount, service: CartServiceDep):
    """Add a product, or increase its quantity if it is already in the cart."""
    return await service.add_item(account.customer_id, data)


@router.put("/cart/items/{product_id}", response_model=CartRead)
async def set_cart_item_quantity(
    product_id: int, data: CartItemQuantity, account: CustomerAccount, service: CartServiceDep
):
    return await service.set_quantity(account.customer_id, product_id, data)


@router.delete("/cart/items/{product_id}", response_model=CartRead)
async def remove_cart_item(product_id: int, account: CustomerAccount, service: CartServiceDep):
    return await service.remove_item(account.customer_id, product_id)


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(account: CustomerAccount, service: CartServiceDep):
    await service.clear(account.customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Orders ----------------------------------------------------------------------

@router.post("/orders", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
async def checkout(account: CustomerAccount, service: OrderServiceDep, data: CheckoutRequest = CheckoutRequest()):
    """Place an order from the whole cart. The body is optional."""
    return await service.checkout(account.customer_id, data)


@router.get("/orders", response_model=list[OrderDetail])
async def list_orders(
    account: CustomerAccount,
    service: OrderServiceDep,
    order_status: OrderStatus | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Order history, newest first."""
    return await service.list_orders(account.customer_id, order_status, offset, limit)


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order(order_id: int, account: CustomerAccount, service: OrderServiceDep):
    return await service.get_order(account.customer_id, order_id)


@router.post("/orders/{order_id}/pay", response_model=OrderDetail)
async def pay_order(order_id: int, account: CustomerAccount, service: OrderServiceDep):
    """Simulate payment of a pending order."""
    return await service.pay(account.customer_id, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderDetail)
async def cancel_order(order_id: int, account: CustomerAccount, service: OrderServiceDep):
    """Cancel a new order. Stock is returned and a paid order becomes refunded."""
    return await service.cancel(account.customer_id, order_id)
