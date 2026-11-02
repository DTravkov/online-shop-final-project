from sqlalchemy import create_engine, inspect
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

import app.models
from app.core.db import Base


def test_marketplace_tables_are_registered_and_created():
    expected = {
        "customers": {"customer_id", "full_name", "email", "phone", "delivery_address"},
        "sellers": {"seller_id", "store_name", "email", "phone", "rating"},
        "products": {"product_id", "seller_id", "product_name", "price", "stock_quantity"},
        "orders": {
            "order_id", "customer_id", "order_date", "total_amount",
            "order_status", "payment_status",
        },
        "order_items": {"order_item_id", "order_id", "product_id", "quantity", "unit_price"},
    }
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        for table, columns in expected.items():
            assert table in inspector.get_table_names()
            assert {column["name"] for column in inspector.get_columns(table)} == columns
            # Check the production dialect as well as actual SQLite creation.
            assert str(CreateTable(Base.metadata.tables[table]).compile(dialect=postgresql.dialect()))
        foreign_keys = {
            (table.name, key.parent.name, key.target_fullname)
            for table in Base.metadata.tables.values()
            for key in table.foreign_keys
        }
        assert foreign_keys == {
            ("products", "seller_id", "sellers.seller_id"),
            ("orders", "customer_id", "customers.customer_id"),
            ("order_items", "order_id", "orders.order_id"),
            ("order_items", "product_id", "products.product_id"),
        }
    finally:
        engine.dispose()
