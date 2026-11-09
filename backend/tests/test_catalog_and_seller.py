from conftest import add_product, register_customer, register_seller


def test_seller_manages_own_products(api):
    seller = register_seller(api)
    other = register_seller(api, email="other@test.local", store_name="Other")

    product = add_product(seller, name="Laptop", price="450000.00", stock=3)
    assert product["seller_id"] == seller.seller_id
    assert product["is_active"] is True

    updated = seller.patch(
        f"/seller/products/{product['product_id']}", json={"price": "430000.50", "stock_quantity": 7}
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "430000.50"
    assert updated.json()["stock_quantity"] == 7
    assert updated.json()["product_name"] == "Laptop"

    assert other.patch(f"/seller/products/{product['product_id']}", json={"price": "1.00"}).status_code == 403
    assert other.delete(f"/seller/products/{product['product_id']}").status_code == 403
    assert seller.patch("/seller/products/999999", json={"price": "1.00"}).status_code == 404
    assert seller.patch(f"/seller/products/{product['product_id']}", json={"stock_quantity": -1}).status_code == 422

    assert [p["product_id"] for p in seller.get("/seller/products").json()] == [product["product_id"]]
    assert other.get("/seller/products").json() == []


def test_withdrawn_product_leaves_catalog_and_carts(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    product = add_product(seller, name="Kettle", stock=5)
    buyer.post("/customer/cart/items", json={"product_id": product["product_id"], "quantity": 2})

    assert seller.delete(f"/seller/products/{product['product_id']}").status_code == 204

    assert api.get("/catalog/products").json() == []
    assert api.get(f"/catalog/products/{product['product_id']}").status_code == 404
    assert buyer.get("/customer/cart").json()["items"] == []
    assert buyer.post("/customer/cart/items", json={"product_id": product["product_id"]}).status_code == 404
    assert seller.get("/seller/products").json() == []
    withdrawn = seller.get("/seller/products", params={"include_inactive": True}).json()
    assert [(p["product_id"], p["is_active"]) for p in withdrawn] == [(product["product_id"], False)]

    restored = seller.patch(f"/seller/products/{product['product_id']}", json={"is_active": True})
    assert restored.json()["is_active"] is True
    assert len(api.get("/catalog/products").json()) == 1


def test_catalog_search_filters_and_sorting(api):
    alpha = register_seller(api, email="alpha@test.local", store_name="Alpha")
    beta = register_seller(api, email="beta@test.local", store_name="Beta")
    add_product(alpha, name="iPhone 15 Case", price="5000.00", stock=10)
    add_product(beta, name="Samsung charger", price="3000.00", stock=0)
    add_product(beta, name="IPHONE 15 case", price="4500.00", stock=4)
    add_product(alpha, name="100% cotton shirt", price="9000.00", stock=1)

    found = api.get("/catalog/products", params={"search": "iphone", "sort": "price_asc"}).json()
    assert [(p["product_name"], p["store_name"]) for p in found] == [
        ("IPHONE 15 case", "Beta"),
        ("iPhone 15 Case", "Alpha"),
    ]
    assert found[0]["seller_rating"] == "0.0"

    # LIKE wildcards in the search text are matched literally.
    assert [p["product_name"] for p in api.get("/catalog/products", params={"search": "%"}).json()] == [
        "100% cotton shirt"
    ]
    in_stock = api.get("/catalog/products", params={"in_stock": True}).json()
    assert "Samsung charger" not in [p["product_name"] for p in in_stock]
    by_seller = api.get("/catalog/products", params={"seller_id": beta.seller_id}).json()
    assert {p["store_name"] for p in by_seller} == {"Beta"}
    expensive_first = api.get("/catalog/products", params={"sort": "price_desc", "limit": 1}).json()
    assert expensive_first[0]["price"] == "9000.00"


def test_product_card_lists_all_sellers_of_the_product(api):
    alpha = register_seller(api, email="alpha@test.local", store_name="Alpha")
    beta = register_seller(api, email="beta@test.local", store_name="Beta")
    first = add_product(alpha, name="AirPods Pro", price="120000.00", stock=2)
    add_product(beta, name="airpods pro", price="115000.00", stock=8)
    add_product(beta, name="AirPods Max", price="300000.00", stock=1)

    card = api.get(f"/catalog/products/{first['product_id']}")
    assert card.status_code == 200
    body = card.json()
    assert body["store_name"] == "Alpha"
    assert body["stock_quantity"] == 2
    assert body["in_stock"] is True
    assert [(offer["store_name"], offer["price"]) for offer in body["offers"]] == [
        ("Beta", "115000.00"),
        ("Alpha", "120000.00"),
    ]


def test_seller_store_profile_update_keeps_rating(api):
    seller = register_seller(api)
    response = seller.patch("/seller/profile", json={"store_name": "Mega Store", "rating": "5.0"})
    assert response.status_code == 200
    assert response.json()["store_name"] == "Mega Store"
    assert response.json()["rating"] == "0.0"
