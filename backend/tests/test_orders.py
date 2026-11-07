from conftest import add_product, login_admin, register_customer, register_seller


def _stock(api, product_id: int) -> int:
    return api.get(f"/catalog/products/{product_id}").json()["stock_quantity"]


def _two_seller_cart(api):
    alpha = register_seller(api, email="alpha@test.local", store_name="Alpha")
    beta = register_seller(api, email="beta@test.local", store_name="Beta")
    buyer = register_customer(api)
    phone = add_product(alpha, name="Phone", price="100000.00", stock=5)
    cable = add_product(beta, name="Cable", price="1999.99", stock=10)
    buyer.post("/customer/cart/items", json={"product_id": phone["product_id"], "quantity": 1})
    buyer.post("/customer/cart/items", json={"product_id": cable["product_id"], "quantity": 2})
    return alpha, beta, buyer, phone, cable


def test_cart_from_several_sellers(api):
    alpha, beta, buyer, phone, cable = _two_seller_cart(api)

    cart = buyer.post("/customer/cart/items", json={"product_id": phone["product_id"], "quantity": 1}).json()
    assert {(item["store_name"], item["quantity"]) for item in cart["items"]} == {("Alpha", 2), ("Beta", 2)}
    assert cart["total_quantity"] == 4
    assert cart["total_amount"] == "203999.98"
    assert cart["can_checkout"] is True

    too_many = buyer.put(f"/customer/cart/items/{phone['product_id']}", json={"quantity": 6})
    assert too_many.status_code == 400
    assert "available 5" in too_many.json()["detail"]

    cart = buyer.put(f"/customer/cart/items/{cable['product_id']}", json={"quantity": 5}).json()
    assert cart["total_amount"] == "209999.95"

    cart = buyer.delete(f"/customer/cart/items/{cable['product_id']}").json()
    assert [item["product_id"] for item in cart["items"]] == [phone["product_id"]]
    assert buyer.delete(f"/customer/cart/items/{cable['product_id']}").status_code == 404

    assert buyer.delete("/customer/cart").status_code == 204
    assert buyer.get("/customer/cart").json() == {
        "items": [], "total_quantity": 0, "total_amount": "0.00", "can_checkout": False,
    }


def test_checkout_creates_one_order_and_reserves_stock(api):
    alpha, beta, buyer, phone, cable = _two_seller_cart(api)

    response = buyer.post("/customer/orders", json={"payment_status": "paid"})
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["customer_id"] == buyer.customer_id
    assert order["order_status"] == "new"
    assert order["payment_status"] == "paid"
    assert order["total_amount"] == "103999.98"
    assert order["delivery_address"] == "Almaty, Abay 1"
    assert {(item["store_name"], item["quantity"], item["unit_price"]) for item in order["items"]} == {
        ("Alpha", 1, "100000.00"),
        ("Beta", 2, "1999.99"),
    }

    assert _stock(api, phone["product_id"]) == 4
    assert _stock(api, cable["product_id"]) == 8
    assert buyer.get("/customer/cart").json()["items"] == []

    # Later price changes do not touch the placed order.
    alpha.patch(f"/seller/products/{phone['product_id']}", json={"price": "1.00"})
    assert buyer.get(f"/customer/orders/{order['order_id']}").json()["total_amount"] == "103999.98"


def test_checkout_rules(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    other_buyer = register_customer(api, email="second@test.local")
    product = add_product(seller, name="Last item", stock=1)

    assert buyer.post("/customer/orders").status_code == 400  # empty cart; the body is optional

    buyer.post("/customer/cart/items", json={"product_id": product["product_id"]})
    other_buyer.post("/customer/cart/items", json={"product_id": product["product_id"]})
    first = buyer.post("/customer/orders", json={"delivery_address": "Shymkent, Tauke Khan 10"})
    assert first.status_code == 201
    assert first.json()["delivery_address"] == "Shymkent, Tauke Khan 10"
    assert first.json()["payment_status"] == "pending"

    # The second buyer's cart now exceeds the stock; nothing is ordered or changed.
    assert other_buyer.get("/customer/cart").json()["can_checkout"] is False
    late = other_buyer.post("/customer/orders", json={})
    assert late.status_code == 400
    assert "Not enough stock" in late.json()["detail"]
    assert other_buyer.get("/customer/orders").json() == []
    assert len(other_buyer.get("/customer/cart").json()["items"]) == 1


def test_order_history_payment_and_cancellation(api):
    alpha, beta, buyer, phone, cable = _two_seller_cart(api)
    first = buyer.post("/customer/orders", json={}).json()
    buyer.post("/customer/cart/items", json={"product_id": cable["product_id"], "quantity": 1})
    second = buyer.post("/customer/orders", json={"payment_status": "paid"}).json()

    history = buyer.get("/customer/orders").json()
    assert [order["order_id"] for order in history] == [second["order_id"], first["order_id"]]
    assert [o["order_id"] for o in buyer.get("/customer/orders", params={"order_status": "cancelled"}).json()] == []

    paid = buyer.post(f"/customer/orders/{first['order_id']}/pay")
    assert paid.status_code == 200 and paid.json()["payment_status"] == "paid"
    assert buyer.post(f"/customer/orders/{first['order_id']}/pay").status_code == 400

    cancelled = buyer.post(f"/customer/orders/{second['order_id']}/cancel").json()
    assert cancelled["order_status"] == "cancelled"
    assert cancelled["payment_status"] == "refunded"
    assert _stock(api, cable["product_id"]) == 8  # 10 - 2 (first order); the second was returned
    assert buyer.post(f"/customer/orders/{second['order_id']}/cancel").status_code == 400

    stranger = register_customer(api, email="stranger@test.local")
    assert stranger.get(f"/customer/orders/{first['order_id']}").status_code == 404
    assert stranger.post(f"/customer/orders/{first['order_id']}/cancel").status_code == 404


def test_seller_sees_and_processes_orders_with_own_items(api):
    alpha, beta, buyer, phone, cable = _two_seller_cart(api)
    outsider = register_seller(api, email="outsider@test.local", store_name="Outsider")
    order = buyer.post("/customer/orders", json={}).json()

    alpha_orders = alpha.get("/seller/orders").json()
    assert len(alpha_orders) == 1
    assert alpha_orders[0]["customer_name"] == "Aigerim Buyer"
    assert alpha_orders[0]["delivery_address"] == "Almaty, Abay 1"
    assert [item["product_name"] for item in alpha_orders[0]["items"]] == ["Phone"]
    assert alpha_orders[0]["seller_total"] == "100000.00"
    assert beta.get(f"/seller/orders/{order['order_id']}").json()["seller_total"] == "3999.98"

    assert outsider.get("/seller/orders").json() == []
    assert outsider.get(f"/seller/orders/{order['order_id']}").status_code == 404
    assert outsider.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "shipped"}).status_code == 404

    shipped = alpha.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "shipped"})
    assert shipped.status_code == 200 and shipped.json()["order_status"] == "shipped"
    assert buyer.get(f"/customer/orders/{order['order_id']}").json()["order_status"] == "shipped"
    assert buyer.post(f"/customer/orders/{order['order_id']}/cancel").status_code == 400

    assert beta.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "delivered"}).status_code == 200
    back = alpha.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "shipped"})
    assert back.status_code == 400
    assert alpha.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "cancelled"}).status_code == 422
    assert [o["order_id"] for o in alpha.get("/seller/orders", params={"order_status": "delivered"}).json()] == [
        order["order_id"]
    ]


def test_seller_cannot_process_cancelled_order(api):
    alpha, beta, buyer, phone, cable = _two_seller_cart(api)
    order = buyer.post("/customer/orders", json={}).json()
    buyer.post(f"/customer/orders/{order['order_id']}/cancel")
    response = alpha.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "shipped"})
    assert response.status_code == 400


def test_admin_payment_status_control(api):
    alpha, beta, buyer, phone, cable = _two_seller_cart(api)
    admin = login_admin(api)
    order = buyer.post("/customer/orders", json={}).json()
    url = f"/admin/orders/{order['order_id']}/payment-status"

    assert admin.patch(url, json={"payment_status": "refunded"}).status_code == 400
    assert admin.patch(url, json={"payment_status": "paid"}).json()["payment_status"] == "paid"
    assert admin.patch(url, json={"payment_status": "pending"}).status_code == 400
    assert admin.patch(url, json={"payment_status": "refunded"}).json()["payment_status"] == "refunded"
    assert admin.patch(url, json={"payment_status": "paid"}).status_code == 400
    assert admin.patch("/admin/orders/999999/payment-status", json={"payment_status": "paid"}).status_code == 404

    pending = admin.get("/admin/orders", params={"payment_status": "refunded"}).json()
    assert [o["order_id"] for o in pending] == [order["order_id"]]
    detail = admin.get(f"/admin/orders/{order['order_id']}").json()
    assert len(detail["items"]) == 2


def test_admin_analytics(api):
    alpha = register_seller(api, email="alpha@test.local", store_name="Alpha")
    buyer = register_customer(api)
    admin = login_admin(api)
    products = [add_product(alpha, name=f"Item {n}", price=f"{n}0.00", stock=100) for n in range(1, 8)]

    def buy(quantities: dict[int, int], payment="pending"):
        for index, quantity in quantities.items():
            buyer.post("/customer/cart/items", json={"product_id": products[index]["product_id"], "quantity": quantity})
        return buyer.post("/customer/orders", json={"payment_status": payment}).json()

    buy({0: 5, 1: 4, 2: 3}, payment="paid")          # 50 + 80 + 90 = 220.00
    buy({3: 2, 4: 1, 1: 2})                           # 80 + 50 + 40 = 170.00
    cancelled = buy({6: 50}, payment="paid")          # cancelled: must not count
    buyer.post(f"/customer/orders/{cancelled['order_id']}/cancel")
    buy({5: 1}, payment="paid")                       # 60.00

    top = admin.get("/admin/analytics/top-products").json()
    assert [(row["product_name"], row["units_sold"]) for row in top] == [
        # Ties on units go to the higher revenue: Item 6 (60.00) beats Item 5 (50.00).
        ("Item 2", 6), ("Item 1", 5), ("Item 3", 3), ("Item 4", 2), ("Item 6", 1),
    ]
    assert top[0]["revenue"] == "120.00"
    assert top[0]["store_name"] == "Alpha"
    assert len(admin.get("/admin/analytics/top-products", params={"limit": 10}).json()) == 6

    summary = admin.get("/admin/analytics/summary").json()
    assert summary["users"] == {"customers": 1, "sellers": 1, "accounts": 3}
    assert summary["products"] == {"total": 7, "active": 7, "out_of_stock": 0}
    assert summary["orders"] == {
        "total": 4,
        "by_order_status": {"new": 3, "shipped": 0, "delivered": 0, "cancelled": 1},
        "by_payment_status": {"pending": 1, "paid": 2, "refunded": 1},
        "items_sold": 18,
        "paid_revenue": "280.00",
        "average_paid_order": "140.00",
    }


def test_admin_summary_on_empty_platform(api):
    summary = login_admin(api).get("/admin/analytics/summary").json()
    assert summary["orders"]["total"] == 0
    assert summary["orders"]["paid_revenue"] == "0.00"
    assert summary["orders"]["average_paid_order"] == "0.00"
    assert login_admin(api).get("/admin/analytics/top-products").json() == []
