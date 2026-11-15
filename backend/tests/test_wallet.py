from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import add_product, deposit, login_admin, register_customer, register_seller


def balance(actor):
    response = actor.get("/wallet")
    assert response.status_code == 200, response.text
    return response.json()["balance"]


def checkout(buyer, seller, *, paid=False, price="10.25", quantity=2, stock=20):
    product = add_product(seller, price=price, stock=stock)
    assert buyer.post("/customer/cart/items", json={
        "product_id": product["product_id"], "quantity": quantity,
    }).status_code == 200
    response = buyer.post("/customer/orders", json={"payment_status": "paid" if paid else "pending"})
    assert response.status_code == 201, response.text
    return response.json(), product


def test_every_account_has_a_private_wallet_and_can_deposit(api):
    actors = [register_customer(api), register_seller(api), login_admin(api)]
    assert api.get("/wallet").status_code == 401
    assert api.post("/wallet/deposit", json={"amount": "10"}).status_code == 401
    assert api.get("/wallet/transactions").status_code == 401
    for actor in actors:
        assert balance(actor) == "0.00"
        assert actor.get("/wallet/transactions").json() == []
        assert deposit(actor, "12.34")["balance"] == "12.34"
        assert deposit(actor, "0.01")["balance"] == "12.35"
        assert actor.get("/auth/me").json()["balance"] == "12.35"
        history = actor.get("/wallet/transactions?limit=1").json()
        assert len(history) == 1
        assert history[0]["kind"] == "deposit" and history[0]["amount"] == "0.01"
        assert "account_id" not in history[0]
        assert actor.get("/wallet/transactions?offset=1&limit=1").json()[0]["amount"] == "12.34"
        assert actor.get("/wallet/transactions?offset=-1").status_code == 422


@pytest.mark.parametrize("amount", ["0", "-1", "0.001", "1000000000000", "NaN", "Infinity", True, None, "oops"])
def test_invalid_deposit_changes_nothing(api, amount):
    buyer = register_customer(api)
    assert buyer.post("/wallet/deposit", json={"amount": amount}).status_code == 422
    assert balance(buyer) == "0.00"
    assert buyer.get("/wallet/transactions").json() == []


def test_deposit_cannot_overflow_balance(api):
    buyer = register_customer(api)
    deposit(buyer, "999999999999.99")
    assert buyer.post("/wallet/deposit", json={"amount": "0.01"}).status_code == 400
    assert balance(buyer) == "999999999999.99"
    assert len(buyer.get("/wallet/transactions").json()) == 1


def test_paid_checkout_splits_revenue_by_original_seller(api):
    buyer = register_customer(api)
    alpha = register_seller(api)
    beta = register_seller(api, email="beta@test.local")
    deposit(buyer, "100.00")
    for seller, price, quantity in ((alpha, "10.25", 2), (beta, "3.33", 3)):
        product = add_product(seller, price=price)
        buyer.post("/customer/cart/items", json={"product_id": product["product_id"], "quantity": quantity})
    response = buyer.post("/customer/orders", json={"payment_status": "paid"})
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["total_amount"] == "30.49"
    assert balance(buyer) == "69.51"
    assert balance(alpha) == "20.50"
    assert balance(beta) == "9.99"
    for actor, kind, amount in ((buyer, "payment", "-30.49"), (alpha, "sale", "20.50"), (beta, "sale", "9.99")):
        entry = actor.get("/wallet/transactions").json()[0]
        assert (entry["order_id"], entry["kind"], entry["amount"]) == (order["order_id"], kind, amount)
    assert buyer.post(f"/customer/orders/{order['order_id']}/pay").status_code == 400
    assert balance(buyer) == "69.51" and balance(alpha) == "20.50"


def test_failed_paid_checkout_rolls_back_stock_cart_orders_and_money(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    product = add_product(seller, price="10.00", stock=3)
    buyer.post("/customer/cart/items", json={"product_id": product["product_id"]})
    response = buyer.post("/customer/orders", json={"payment_status": "paid"})
    assert response.status_code == 400 and "Insufficient balance" in response.json()["detail"]
    assert buyer.get("/customer/orders").json() == []
    assert seller.get("/seller/orders").json() == []
    assert api.get(f"/catalog/products/{product['product_id']}").json()["stock_quantity"] == 3
    assert buyer.get("/customer/cart").json()["total_quantity"] == 1
    assert balance(buyer) == balance(seller) == "0.00"
    assert buyer.get("/wallet/transactions").json() == seller.get("/wallet/transactions").json() == []


def test_pending_order_pays_later_and_paid_cancellation_reverses_transfers(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    order, product = checkout(buyer, seller)
    assert balance(buyer) == balance(seller) == "0.00"
    url = f"/customer/orders/{order['order_id']}"
    assert buyer.post(url + "/pay").status_code == 400
    assert buyer.get(url).json()["payment_status"] == "pending"
    deposit(buyer, "20.50")
    assert buyer.post(url + "/pay").status_code == 200
    assert balance(buyer) == "0.00" and balance(seller) == "20.50"
    response = buyer.post(url + "/cancel")
    assert response.status_code == 200 and response.json()["payment_status"] == "refunded"
    assert balance(buyer) == "20.50" and balance(seller) == "0.00"
    assert api.get(f"/catalog/products/{product['product_id']}").json()["stock_quantity"] == 20
    assert buyer.post(url + "/cancel").status_code == 400
    assert buyer.get("/wallet/transactions").json()[0]["kind"] == "refund"
    assert seller.get("/wallet/transactions").json()[0]["kind"] == "sale_refund"


def test_admin_payment_requires_funds_and_refund_does_not_refund_twice_on_cancel(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    admin = login_admin(api)
    order, _product = checkout(buyer, seller)
    url = f"/admin/orders/{order['order_id']}/payment-status"
    assert admin.patch(url, json={"payment_status": "paid"}).status_code == 400
    deposit(buyer, "30.00")
    assert admin.patch(url, json={"payment_status": "paid"}).status_code == 200
    assert balance(buyer) == "9.50" and balance(seller) == "20.50"
    assert admin.patch(url, json={"payment_status": "refunded"}).status_code == 200
    assert balance(buyer) == "30.00" and balance(seller) == "0.00"
    assert buyer.post(f"/customer/orders/{order['order_id']}/cancel").status_code == 200
    assert balance(buyer) == "30.00"
    assert admin.patch(url, json={"payment_status": "refunded"}).status_code == 400
    assert len(buyer.get("/wallet/transactions").json()) == 3


def test_refund_uses_original_payouts_after_raw_order_items_change(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    admin = login_admin(api)
    deposit(buyer, "100.00")
    order, product = checkout(buyer, seller, paid=True)
    assert admin.put(f"/order-items/{order['items'][0]['order_item_id']}", json={
        "order_id": order["order_id"], "product_id": product["product_id"], "quantity": 1, "unit_price": "1.00",
    }).status_code == 200
    response = admin.patch(f"/admin/orders/{order['order_id']}/payment-status", json={"payment_status": "refunded"})
    assert response.status_code == 200
    assert balance(buyer) == "100.00" and balance(seller) == "0.00"


def test_ledger_blocks_payment_again_after_raw_status_reset(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    deposit(buyer, "100.00")
    order, _product = checkout(buyer, seller, paid=True)
    values = {key: order[key] for key in (
        "customer_id", "order_date", "total_amount", "payment_status", "delivery_address", "order_status",
    )}
    values["payment_status"] = "pending"
    assert login_admin(api).put(f"/orders/{order['order_id']}", json=values).status_code == 200
    assert buyer.post(f"/customer/orders/{order['order_id']}/pay").status_code == 400
    assert balance(buyer) == "79.50" and balance(seller) == "20.50"


def test_free_order_requires_no_deposit(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    order, _product = checkout(buyer, seller, paid=True, price="0.00")
    assert order["payment_status"] == "paid"
    assert balance(buyer) == balance(seller) == "0.00"


def test_concurrent_deposits_do_not_lose_money(api):
    buyer = register_customer(api)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: buyer.post("/wallet/deposit", json={"amount": "0.01"}), range(8)))
    assert all(response.status_code == 200 for response in responses)
    assert balance(buyer) == "0.08"
    assert len(buyer.get("/wallet/transactions").json()) == 8


def test_concurrent_payments_cannot_spend_same_balance_twice(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    deposit(buyer, "20.50")
    orders = [checkout(buyer, seller)[0] for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda order: buyer.post(f"/customer/orders/{order['order_id']}/pay"), orders))
    assert sorted(response.status_code for response in responses) == [200, 400]
    assert balance(buyer) == "0.00" and balance(seller) == "20.50"


def test_transfer_failure_after_ledger_flush_rolls_back(api, monkeypatch):
    from app.exceptions import BusinessRuleViolation
    from app.repository.order import OrderRepository

    buyer = register_customer(api)
    seller = register_seller(api)
    deposit(buyer, "100.00")
    order, _product = checkout(buyer, seller)

    async def fail_update(*_args):
        raise BusinessRuleViolation("Injected failure after payment ledger flush")

    with monkeypatch.context() as patch:
        patch.setattr(OrderRepository, "update", fail_update)
        assert buyer.post(f"/customer/orders/{order['order_id']}/pay").status_code == 400
    assert balance(buyer) == "100.00" and balance(seller) == "0.00"
    assert buyer.get(f"/customer/orders/{order['order_id']}").json()["payment_status"] == "pending"
    assert [row["kind"] for row in buyer.get("/wallet/transactions").json()] == ["deposit"]
    assert seller.get("/wallet/transactions").json() == []


def test_concurrent_buyers_credit_shared_seller_without_lost_revenue(api):
    seller = register_seller(api)
    buyers = [register_customer(api, email=f"buyer{index}@test.local") for index in range(2)]
    orders = []
    for buyer in buyers:
        deposit(buyer, "20.50")
        orders.append(checkout(buyer, seller)[0])

    def pay(pair):
        buyer, order = pair
        return buyer.post(f"/customer/orders/{order['order_id']}/pay")

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(pay, zip(buyers, orders, strict=True)))
    assert all(response.status_code == 200 for response in responses)
    assert balance(seller) == "41.00"
    assert all(balance(buyer) == "0.00" for buyer in buyers)


def test_seller_balance_overflow_rolls_back_payment_for_every_participant(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    deposit(buyer, "100.00")
    deposit(seller, "999999999999.99")
    order, _product = checkout(buyer, seller)
    assert buyer.post(f"/customer/orders/{order['order_id']}/pay").status_code == 400
    assert balance(buyer) == "100.00" and balance(seller) == "999999999999.99"
    assert buyer.get(f"/customer/orders/{order['order_id']}").json()["payment_status"] == "pending"
    assert len(buyer.get("/wallet/transactions").json()) == len(seller.get("/wallet/transactions").json()) == 1
