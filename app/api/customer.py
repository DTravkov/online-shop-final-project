from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.service.customer import CustomerService, get_customer_service

router = APIRouter(prefix="/customers", tags=["customers"])
CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(data: CustomerCreate, service: CustomerServiceDep):
    return await service.create(data)


@router.get("", response_model=list[CustomerRead])
async def list_records(
    service: CustomerServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list(offset, limit)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: int, service: CustomerServiceDep):
    return await service.get(customer_id)


@router.put("/{customer_id}", response_model=CustomerRead)
async def update_customer(customer_id: int, data: CustomerUpdate, service: CustomerServiceDep):
    return await service.update(customer_id, data)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: int, service: CustomerServiceDep):
    await service.delete(customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
