# Methods named "list" shadow the builtin inside the class body; defer annotations.
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.product import Product
from app.models.seller import Seller

CatalogSort = Literal["id", "price_asc", "price_desc", "name"]


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("Product conflicts with related records.") from exc

    async def list(self, offset: int, limit: int) -> list[Product]:
        result = await self.db.scalars(
            select(Product).order_by(Product.product_id).offset(offset).limit(limit)
        )
        return list(result.all())

    async def get(self, product_id: int) -> Product | None:
        return await self.db.get(Product, product_id)

    async def create(self, values: dict[str, Any]) -> Product:
        record = Product(**values)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: Product, values: dict[str, Any]) -> Product:
        for field, value in values.items():
            setattr(record, field, value)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: Product) -> None:
        await self.db.delete(record)
        await self.db.flush()

    async def search_catalog(
        self,
        search: str | None,
        seller_id: int | None,
        in_stock_only: bool,
        sort: CatalogSort,
        offset: int,
        limit: int,
    ) -> list[tuple[Product, Seller]]:
        query = (
            select(Product, Seller)
            .join(Seller, Seller.seller_id == Product.seller_id)
            .where(Product.is_active.is_(True))
        )
        if search:
            query = query.where(Product.product_name.icontains(search, autoescape=True))
        if seller_id is not None:
            query = query.where(Product.seller_id == seller_id)
        if in_stock_only:
            query = query.where(Product.stock_quantity > 0)
        order_by = {
            "id": [Product.product_id],
            "price_asc": [Product.price, Product.product_id],
            "price_desc": [Product.price.desc(), Product.product_id],
            "name": [func.lower(Product.product_name), Product.product_id],
        }[sort]
        result = await self.db.execute(query.order_by(*order_by).offset(offset).limit(limit))
        return [tuple(row) for row in result.all()]

    async def get_with_seller(self, product_id: int) -> tuple[Product, Seller] | None:
        row = (
            await self.db.execute(
                select(Product, Seller)
                .join(Seller, Seller.seller_id == Product.seller_id)
                .where(Product.product_id == product_id)
            )
        ).first()
        return tuple(row) if row is not None else None

    async def list_offers(self, product_name: str) -> list[tuple[Product, Seller]]:
        """Active listings of the same product by any seller, matched by name ignoring case."""
        result = await self.db.execute(
            select(Product, Seller)
            .join(Seller, Seller.seller_id == Product.seller_id)
            .where(
                Product.is_active.is_(True),
                func.lower(func.trim(Product.product_name)) == product_name.strip().lower(),
            )
            .order_by(Product.price, Product.product_id)
        )
        return [tuple(row) for row in result.all()]

    async def list_by_seller(
        self, seller_id: int, include_inactive: bool, offset: int, limit: int
    ) -> list[Product]:
        query = select(Product).where(Product.seller_id == seller_id)
        if not include_inactive:
            query = query.where(Product.is_active.is_(True))
        result = await self.db.scalars(query.order_by(Product.product_id).offset(offset).limit(limit))
        return list(result.all())

    async def get_many_for_update(self, product_ids: list[int]) -> list[Product]:
        """Lock product rows in a fixed order so concurrent checkouts cannot oversell."""
        if not product_ids:
            return []
        result = await self.db.scalars(
            select(Product)
            .where(Product.product_id.in_(product_ids))
            .order_by(Product.product_id)
            .with_for_update()
        )
        return list(result.all())


def get_product_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> ProductRepository:
    return ProductRepository(db)
