from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import add_product, deposit, login_admin, register_customer, register_seller


def buy(buyer, seller, *, payment="paid"):
    deposit(buyer, "1000.00")
    product = add_product(seller)
    assert buyer.post("/customer/cart/items", json={"product_id": product["product_id"]}).status_code == 200
    response = buyer.post("/customer/orders", json={"payment_status": payment})
    assert response.status_code == 201, response.text
    return response.json()


def deliver(seller, order):
    response = seller.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "delivered"})
    assert response.status_code == 200, response.text


def test_shop_is_public_and_does_not_expose_private_profiles(api):
    seller = register_seller(api, store_name="Small Shop")
    response = api.get(f"/catalog/sellers/{seller.seller_id}")
    assert response.status_code == 200
    assert response.json() == {
        "seller_id": seller.seller_id, "store_name": "Small Shop", "rating": "0.0", "review_count": 0,
    }
    assert api.get(f"/catalog/sellers/{seller.seller_id}/reviews").json() == []
    assert api.get("/catalog/sellers/99999").status_code == 404
    assert api.get("/catalog/sellers/99999/reviews").status_code == 404


def test_only_paid_delivered_buyers_can_review_and_each_seller_is_independent(api):
    alpha = register_seller(api)
    beta = register_seller(api, email="beta@test.local")
    buyer = register_customer(api)
    path = f"/customer/sellers/{alpha.seller_id}/review"
    payload = {"rating": 5, "comment": "Lovely shop"}
    assert api.put(path, json=payload).status_code == 401
    assert alpha.put(path, json=payload).status_code == 403
    assert login_admin(api).put(path, json=payload).status_code == 403
    assert buyer.get(path).json() == {"can_review": False, "review": None}
    assert buyer.put(path, json=payload).status_code == 400

    order = buy(buyer, alpha, payment="pending")
    assert buyer.put(path, json=payload).status_code == 400
    deliver(alpha, order)
    assert buyer.put(path, json=payload).status_code == 400
    assert buyer.post(f"/customer/orders/{order['order_id']}/pay").status_code == 200
    assert buyer.get(path).json()["can_review"] is True
    assert buyer.put(path, json=payload).status_code == 200
    assert buyer.put(f"/customer/sellers/{beta.seller_id}/review", json=payload).status_code == 400
    outsider = register_customer(api, email="outsider@test.local")
    assert outsider.put(path, json=payload).status_code == 400
    assert outsider.delete(path).status_code == 404


def test_review_edit_delete_rating_and_public_pagination(api):
    seller = register_seller(api)
    first = register_customer(api, full_name="First Buyer")
    second = register_customer(api, email="second@test.local", full_name="Second Buyer")
    for buyer in (first, second):
        deliver(seller, buy(buyer, seller))
    path = f"/customer/sellers/{seller.seller_id}/review"
    original = first.put(path, json={"rating": 5, "comment": "  Great service  "}).json()
    assert original["comment"] == "Great service"
    second.put(path, json={"rating": 4, "comment": "Good"})
    public_path = f"/catalog/sellers/{seller.seller_id}"
    assert api.get(public_path).json()["rating"] == "4.5"
    assert api.get(public_path).json()["review_count"] == 2
    assert seller.get("/seller/profile").json()["rating"] == "4.5"
    assert api.get("/catalog/products").json()[0]["seller_rating"] == "4.5"
    rows = api.get(public_path + "/reviews?limit=1").json()
    assert len(rows) == 1 and rows[0]["customer_name"] == "Second Buyer"
    assert "customer_id" not in rows[0] and "email" not in rows[0]
    assert api.get(public_path + "/reviews?limit=1&offset=1").json()[0]["customer_name"] == "First Buyer"
    assert api.get(public_path + "/reviews?offset=-1").status_code == 422

    edited = first.put(path, json={"rating": 2, "comment": "Updated experience"}).json()
    assert edited["review_id"] == original["review_id"]
    assert edited["created_at"] == original["created_at"]
    assert api.get(public_path).json()["review_count"] == 2
    assert api.get(public_path).json()["rating"] == "3.0"
    assert first.delete(path).status_code == 204
    assert api.get(public_path).json()["rating"] == "4.0"
    assert second.delete(path).status_code == 204
    assert api.get(public_path).json()["rating"] == "0.0"
    assert api.get("/catalog/products").json()[0]["seller_rating"] == "0.0"


@pytest.mark.parametrize("payload", [
    {"rating": 0, "comment": "Bad"}, {"rating": 6, "comment": "Good"},
    {"rating": 3.5, "comment": "Good"}, {"rating": True, "comment": "Good"},
    {"rating": 5, "comment": "   "}, {"rating": 5, "comment": "x" * 2001},
])
def test_invalid_review_is_rejected(api, payload):
    buyer = register_customer(api)
    seller = register_seller(api)
    assert buyer.put(f"/customer/sellers/{seller.seller_id}/review", json=payload).status_code == 422


def test_refunded_and_cancelled_orders_do_not_qualify(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    path = f"/customer/sellers/{seller.seller_id}/review"
    cancelled = buy(buyer, seller)
    buyer.post(f"/customer/orders/{cancelled['order_id']}/cancel")
    assert buyer.get(path).json()["can_review"] is False
    delivered = buy(buyer, seller)
    deliver(seller, delivered)
    login_admin(api).patch(f"/admin/orders/{delivered['order_id']}/payment-status", json={"payment_status": "refunded"})
    assert buyer.get(path).json()["can_review"] is False
    assert buyer.put(path, json={"rating": 5, "comment": "Hello"}).status_code == 400


def test_fulfillment_progress_and_reviews_do_not_depend_on_other_sellers(api):
    buyer = register_customer(api)
    deposit(buyer)
    alpha = register_seller(api)
    beta = register_seller(api, email="beta@test.local")
    for seller in (alpha, beta):
        product = add_product(seller)
        buyer.post("/customer/cart/items", json={"product_id": product["product_id"]})
    order = buyer.post("/customer/orders", json={"payment_status": "paid"}).json()
    url = f"/seller/orders/{order['order_id']}/status"
    assert len(order["fulfillments"]) == 2
    alpha.patch(url, json={"order_status": "shipped"})
    beta.patch(url, json={"order_status": "shipped"})
    assert buyer.get(f"/customer/orders/{order['order_id']}").json()["order_status"] == "shipped"
    deliver(alpha, order)
    detail = buyer.get(f"/customer/orders/{order['order_id']}").json()
    assert detail["order_status"] == "partially_delivered"
    assert {row["seller_id"]: row["status"] for row in detail["fulfillments"]} == {
        alpha.seller_id: "delivered", beta.seller_id: "shipped",
    }
    for seller, status in ((alpha, 200), (beta, 400)):
        response = buyer.put(f"/customer/sellers/{seller.seller_id}/review", json={"rating": 5, "comment": "Arrived"})
        assert response.status_code == status
    deliver(beta, order)
    assert buyer.get(f"/customer/orders/{order['order_id']}").json()["order_status"] == "delivered"


def test_cancellation_updates_every_fulfillment(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    order = buy(buyer, seller)
    response = buyer.post(f"/customer/orders/{order['order_id']}/cancel")
    assert response.status_code == 200
    assert [row["status"] for row in response.json()["fulfillments"]] == ["cancelled"]
    assert seller.get(f"/seller/orders/{order['order_id']}").json()["order_status"] == "cancelled"


def test_fulfillment_keeps_original_seller_when_admin_reassigns_listing(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    other = register_seller(api, email="other@test.local")
    order = buy(buyer, seller)
    item = order["items"][0]
    response = login_admin(api).put(f"/products/{item['product_id']}", json={
        "seller_id": other.seller_id, "product_name": "Moved listing", "price": "100.00", "stock_quantity": 9,
    })
    assert response.status_code == 200
    assert seller.get(f"/seller/orders/{order['order_id']}").json()["items"][0]["seller_id"] == seller.seller_id
    assert other.get(f"/seller/orders/{order['order_id']}").status_code == 404
    deliver(seller, order)


def test_concurrent_seller_updates_keep_both_statuses(api):
    buyer = register_customer(api)
    sellers = [register_seller(api, email=f"shop{index}@test.local") for index in range(2)]
    for seller in sellers:
        product = add_product(seller)
        buyer.post("/customer/cart/items", json={"product_id": product["product_id"]})
    order = buyer.post("/customer/orders", json={}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda seller: seller.patch(
            f"/seller/orders/{order['order_id']}/status", json={"order_status": "delivered"},
        ), sellers))
    assert [response.status_code for response in responses] == [200, 200]
    detail = buyer.get(f"/customer/orders/{order['order_id']}").json()
    assert detail["order_status"] == "delivered"
    assert [row["status"] for row in detail["fulfillments"]] == ["delivered", "delivered"]


def test_fulfillment_failure_after_flush_rolls_back(api, monkeypatch):
    from app.exceptions import BusinessRuleViolation
    from app.repository.order import OrderRepository

    seller = register_seller(api)
    buyer = register_customer(api)
    order = buy(buyer, seller)

    async def fail_update(*_args):
        raise BusinessRuleViolation("Injected failure after fulfillment flush")

    with monkeypatch.context() as patch:
        patch.setattr(OrderRepository, "update", fail_update)
        response = seller.patch(f"/seller/orders/{order['order_id']}/status", json={"order_status": "delivered"})
        assert response.status_code == 400
    detail = buyer.get(f"/customer/orders/{order['order_id']}").json()
    assert detail["order_status"] == "new"
    assert detail["fulfillments"][0]["status"] == "new"
    deliver(seller, order)


def test_review_failure_after_flush_rolls_back(api, monkeypatch):
    from app.exceptions import BusinessRuleViolation
    from app.repository.seller import SellerRepository

    seller = register_seller(api)
    buyer = register_customer(api)
    deliver(seller, buy(buyer, seller))

    async def fail_update(*_args):
        raise BusinessRuleViolation("Injected failure after review flush")

    with monkeypatch.context() as patch:
        patch.setattr(SellerRepository, "update", fail_update)
        response = buyer.put(f"/customer/sellers/{seller.seller_id}/review", json={"rating": 5, "comment": "Hello"})
        assert response.status_code == 400
    assert api.get(f"/catalog/sellers/{seller.seller_id}/reviews").json() == []
    assert seller.get("/seller/profile").json()["rating"] == "0.0"


def test_concurrent_reviews_keep_correct_average(api):
    seller = register_seller(api)
    buyers = [register_customer(api, email=f"buyer{index}@test.local") for index in range(2)]
    for buyer in buyers:
        deliver(seller, buy(buyer, seller))

    def review(pair):
        buyer, rating = pair
        return buyer.put(f"/customer/sellers/{seller.seller_id}/review", json={"rating": rating, "comment": "Hello"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(review, zip(buyers, (2, 5), strict=True)))
    assert [response.status_code for response in responses] == [200, 200]
    assert seller.get("/seller/profile").json()["rating"] == "3.5"
    assert api.get(f"/catalog/sellers/{seller.seller_id}").json()["review_count"] == 2


def test_overlapping_checkout_creates_only_one_order(api):
    buyer = register_customer(api)
    product = add_product(register_seller(api), stock=10)
    buyer.post("/customer/cart/items", json={"product_id": product["product_id"]})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _index: buyer.post("/customer/orders", json={}), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 400]
    assert len(buyer.get("/customer/orders").json()) == 1
    assert api.get(f"/catalog/products/{product['product_id']}").json()["stock_quantity"] == 9


def test_raw_cancelled_order_does_not_qualify_even_if_fulfillment_was_delivered(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    order = buy(buyer, seller)
    deliver(seller, order)
    replacement = {key: order[key] for key in (
        "customer_id", "order_date", "total_amount", "payment_status", "delivery_address",
    )}
    replacement["order_status"] = "cancelled"
    assert login_admin(api).put(f"/orders/{order['order_id']}", json=replacement).status_code == 200
    response = buyer.put(f"/customer/sellers/{seller.seller_id}/review", json={"rating": 5, "comment": "Hello"})
    assert response.status_code == 400
