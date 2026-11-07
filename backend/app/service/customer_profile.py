from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.repository.account import AccountRepository, get_account_repository
from app.repository.customer import CustomerRepository, get_customer_repository
from app.schemas.customer import CustomerProfileUpdate, CustomerRead, DeliveryAddress
from app.service.auth import change_account_email


class CustomerProfileService:
    def __init__(self, customers: CustomerRepository, accounts: AccountRepository):
        self.customers = customers
        self.accounts = accounts

    async def _get_record(self, customer_id: int):
        record = await self.customers.get(customer_id)
        if record is None:
            raise RecordNotFound("Customer", customer_id)
        return record

    async def get(self, customer_id: int) -> CustomerRead:
        return CustomerRead.model_validate(await self._get_record(customer_id))

    async def update(self, customer_id: int, data: CustomerProfileUpdate) -> CustomerRead:
        values = data.model_dump(exclude_none=True)
        async with self.customers.transaction():
            record = await self._get_record(customer_id)
            if "email" in values:
                account = await self.accounts.get_by_customer_id(customer_id)
                await change_account_email(self.accounts, account, values["email"])
            record = await self.customers.update(record, values)
            return CustomerRead.model_validate(record)

    async def get_delivery_address(self, customer_id: int) -> DeliveryAddress:
        record = await self._get_record(customer_id)
        return DeliveryAddress(delivery_address=record.delivery_address)

    async def set_delivery_address(self, customer_id: int, data: DeliveryAddress) -> DeliveryAddress:
        async with self.customers.transaction():
            record = await self._get_record(customer_id)
            record = await self.customers.update(record, data.model_dump())
            return DeliveryAddress(delivery_address=record.delivery_address)


def get_customer_profile_service(
    customers: Annotated[CustomerRepository, Depends(get_customer_repository)],
    accounts: Annotated[AccountRepository, Depends(get_account_repository)],
) -> CustomerProfileService:
    return CustomerProfileService(customers, accounts)
