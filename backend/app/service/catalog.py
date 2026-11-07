from typing import Annotated

from fastapi import Depends

from app.exceptions import RecordNotFound
from app.models.product import Product
from app.models.seller import Seller
from app.repository.product import CatalogSort, ProductRepository, get_product_repository
from app.schemas.product import CatalogProduct, ProductCard, ProductOffer


def _catalog_fields(product: Product, seller: Seller) -> dict:
    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "price": product.price,
        "stock_quantity": product.stock_quantity,
        "in_stock": product.stock_quantity > 0,
        "seller_id": seller.seller_id,
        "store_name": seller.store_name,
        "seller_rating": seller.rating,
    }


class CatalogService:
    def __init__(self, products: ProductRepository):
        self.products = products

    async def list_products(
        self,
        search: str | None,
        seller_id: int | None,
        in_stock_only: bool,
        sort: CatalogSort,
        offset: int,
        limit: int,
    ) -> list[CatalogProduct]:
        search = search.strip() if search else None
        rows = await self.products.search_catalog(search, seller_id, in_stock_only, sort, offset, limit)
        return [CatalogProduct(**_catalog_fields(product, seller)) for product, seller in rows]

    async def get_product_card(self, product_id: int) -> ProductCard:
        row = await self.products.get_with_seller(product_id)
        if row is None or not row[0].is_active:
            raise RecordNotFound("Product", product_id)
        product, seller = row
        offers = [
            ProductOffer(
                product_id=offer.product_id,
                seller_id=offer_seller.seller_id,
                store_name=offer_seller.store_name,
                seller_rating=offer_seller.rating,
                price=offer.price,
                stock_quantity=offer.stock_quantity,
            )
            for offer, offer_seller in await self.products.list_offers(product.product_name)
        ]
        return ProductCard(**_catalog_fields(product, seller), offers=offers)


def get_catalog_service(
    products: Annotated[ProductRepository, Depends(get_product_repository)],
) -> CatalogService:
    return CatalogService(products)
