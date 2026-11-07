from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.schemas.analytics import PlatformSummary, TopProduct
from app.schemas.order import OrderDetail, OrderRead, OrderStatus, PaymentStatus, PaymentStatusUpdate
from app.service.admin import AdminService, get_admin_service
from app.service.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


@router.get("/analytics/top-products", response_model=list[TopProduct])
async def top_products(service: AdminServiceDep, limit: Annotated[int, Query(ge=1, le=50)] = 5):
    """Best-selling products by units sold, ignoring cancelled and refunded orders."""
    return await service.top_products(limit)


@router.get("/analytics/summary", response_model=PlatformSummary)
async def platform_summary(service: AdminServiceDep):
    return await service.summary()


@router.get("/orders", response_model=list[OrderRead])
async def list_orders(
    service: AdminServiceDep,
    order_status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list_orders(order_status, payment_status, offset, limit)


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order(order_id: int, service: AdminServiceDep):
    return await service.get_order(order_id)


@router.patch("/orders/{order_id}/payment-status", response_model=OrderRead)
async def update_payment_status(order_id: int, data: PaymentStatusUpdate, service: AdminServiceDep):
    """Allowed: pending → paid, paid → refunded."""
    return await service.update_payment_status(order_id, data)
