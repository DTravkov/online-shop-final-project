from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderCreate, OrderUpdate


@pytest.mark.parametrize("schema", [OrderCreate, OrderUpdate])
@pytest.mark.parametrize("order_date", [
    "2026-11-05T10:31:56.731Z",
    "2026-11-05T15:31:56.731+05:00",
    "2026-11-05T06:31:56.731-04:00",
])
def test_order_date_preserves_the_instant(schema, order_date):
    order = schema(
        customer_id=1,
        order_date=order_date,
        total_amount="0.00",
        order_status="new",
        payment_status="pending",
    )

    assert order.order_date.astimezone(UTC) == datetime(
        2026, 11, 5, 10, 31, 56, 731000, tzinfo=UTC,
    )


@pytest.mark.parametrize("schema", [OrderCreate, OrderUpdate])
def test_order_date_requires_a_timezone(schema):
    with pytest.raises(ValidationError) as error:
        schema(
            customer_id=1,
            order_date="2026-11-05T10:31:56.731",
            total_amount="0.00",
            order_status="new",
            payment_status="pending",
        )

    assert any(
        item["loc"] == ("order_date",) and item["type"] == "timezone_aware"
        for item in error.value.errors()
    )
