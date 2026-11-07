from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.repository.product import CatalogSort
from app.schemas.product import CatalogProduct, ProductCard
from app.service.catalog import CatalogService, get_catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])
CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get("/products", response_model=list[CatalogProduct])
async def list_catalog_products(
    service: CatalogServiceDep,
    search: Annotated[str | None, Query(max_length=150, description="Part of the product name")] = None,
    seller_id: Annotated[int | None, Query(gt=0)] = None,
    in_stock: Annotated[bool, Query(description="Only products with stock")] = False,
    sort: CatalogSort = "id",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return await service.list_products(search, seller_id, in_stock, sort, offset, limit)


@router.get("/products/{product_id}", response_model=ProductCard)
async def get_product_card(product_id: int, service: CatalogServiceDep):
    return await service.get_product_card(product_id)
