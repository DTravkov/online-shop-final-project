from typing import Annotated

from fastapi import Depends

from app.exceptions import PermissionDenied, RecordNotFound
from app.models.product import Product
from app.repository.account import AccountRepository, get_account_repository
from app.repository.cart_item import CartItemRepository, get_cart_item_repository
from app.repository.product import ProductRepository, get_product_repository
from app.repository.seller import SellerRepository, get_seller_repository
from app.schemas.product import ProductRead, SellerProductCreate, SellerProductUpdate
from app.schemas.seller import SellerProfileUpdate, SellerRead
from app.service.auth import change_account_email


class SellerStoreService:
    """Store profile and product listings of the signed-in seller."""

    def __init__(
        self,
        sellers: SellerRepository,
        accounts: AccountRepository,
        products: ProductRepository,
        cart: CartItemRepository,
    ):
        self.sellers = sellers
        self.accounts = accounts
        self.products = products
        self.cart = cart

    async def _get_seller(self, seller_id: int):
        record = await self.sellers.get(seller_id)
        if record is None:
            raise RecordNotFound("Seller", seller_id)
        return record

    async def get_profile(self, seller_id: int) -> SellerRead:
        return SellerRead.model_validate(await self._get_seller(seller_id))

    async def update_profile(self, seller_id: int, data: SellerProfileUpdate) -> SellerRead:
        values = data.model_dump(exclude_none=True)
        async with self.sellers.transaction():
            record = await self._get_seller(seller_id)
            if "email" in values:
                account = await self.accounts.get_by_seller_id(seller_id)
                await change_account_email(self.accounts, account, values["email"])
            record = await self.sellers.update(record, values)
            return SellerRead.model_validate(record)

    async def list_products(
        self, seller_id: int, include_inactive: bool, offset: int, limit: int
    ) -> list[ProductRead]:
        records = await self.products.list_by_seller(seller_id, include_inactive, offset, limit)
        return [ProductRead.model_validate(record) for record in records]

    async def _get_own_product(self, seller_id: int, product_id: int) -> Product:
        product = await self.products.get(product_id)
        if product is None:
            raise RecordNotFound("Product", product_id)
        if product.seller_id != seller_id:
            raise PermissionDenied(f"Product {product_id} belongs to another seller.")
        return product

    async def get_product(self, seller_id: int, product_id: int) -> ProductRead:
        return ProductRead.model_validate(await self._get_own_product(seller_id, product_id))

    async def create_product(self, seller_id: int, data: SellerProductCreate) -> ProductRead:
        async with self.products.transaction():
            record = await self.products.create({**data.model_dump(), "seller_id": seller_id})
            return ProductRead.model_validate(record)

    async def update_product(
        self, seller_id: int, product_id: int, data: SellerProductUpdate
    ) -> ProductRead:
        values = data.model_dump(exclude_none=True)
        async with self.products.transaction():
            record = await self._get_own_product(seller_id, product_id)
            record = await self.products.update(record, values)
            if not record.is_active:
                await self.cart.delete_for_product(product_id)
            return ProductRead.model_validate(record)

    async def withdraw_product(self, seller_id: int, product_id: int) -> None:
        """Take a product off sale. It stays in order history and leaves every cart."""
        async with self.products.transaction():
            record = await self._get_own_product(seller_id, product_id)
            await self.products.update(record, {"is_active": False})
            await self.cart.delete_for_product(product_id)


def get_seller_store_service(
    sellers: Annotated[SellerRepository, Depends(get_seller_repository)],
    accounts: Annotated[AccountRepository, Depends(get_account_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    cart: Annotated[CartItemRepository, Depends(get_cart_item_repository)],
) -> SellerStoreService:
    return SellerStoreService(sellers, accounts, products, cart)
