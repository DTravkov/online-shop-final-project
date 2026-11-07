from conftest import add_product, login_admin, register_customer, register_seller


def test_customer_registration_login_and_me(api):
    buyer = register_customer(api, email="  Buyer@Test.Local ")
    assert buyer.customer_id is not None and buyer.seller_id is None

    duplicate = api.post("/auth/register/seller", json={
        "email": "buyer@test.local", "password": "another-pass", "store_name": "X", "phone": "1",
    })
    assert duplicate.status_code == 409

    login = api.post("/auth/login", json={"email": "BUYER@test.local", "password": "buyer-password"})
    assert login.status_code == 200
    assert login.json()["role"] == "customer"

    me = buyer.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "account_id": buyer.account_id,
        "email": "buyer@test.local",
        "role": "customer",
        "customer_id": buyer.customer_id,
        "seller_id": None,
    }


def test_login_rejects_wrong_password_and_unknown_email(api):
    register_customer(api)
    for payload in (
        {"email": "buyer@test.local", "password": "wrong-password"},
        {"email": "nobody@test.local", "password": "buyer-password"},
    ):
        response = api.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json() == {"detail": "Incorrect email or password."}
        assert response.headers["www-authenticate"] == "Bearer"


def test_registration_validates_input(api):
    response = api.post("/auth/register/customer", json={
        "email": "not-an-email", "password": "short", "full_name": "A", "phone": "1",
        "delivery_address": "x",
    })
    assert response.status_code == 422
    fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert {"email", "password"} <= fields


def test_new_seller_starts_with_zero_rating(api):
    seller = register_seller(api)
    profile = seller.get("/seller/profile").json()
    assert profile["rating"] == "0.0"
    assert profile["store_name"] == "Store"


def test_roles_are_enforced(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    admin = login_admin(api)

    assert api.get("/customer/cart").status_code == 401
    assert api.get("/customer/cart", headers={"Authorization": "Bearer garbage"}).status_code == 401

    assert seller.get("/customer/cart").status_code == 403
    assert buyer.get("/seller/products").status_code == 403
    assert buyer.get("/admin/analytics/summary").status_code == 403
    assert seller.get("/admin/orders").status_code == 403
    assert admin.get("/admin/analytics/summary").status_code == 200


def test_raw_crud_is_admin_only(api):
    buyer = register_customer(api)
    admin = login_admin(api)

    assert api.get("/orders").status_code == 401
    assert buyer.get("/orders").status_code == 403
    assert buyer.put("/products/1", json={}).status_code == 403
    assert admin.get("/customers").status_code == 200
    assert [customer["customer_id"] for customer in admin.get("/customers").json()] == [buyer.customer_id]
    # The independent example resource stays public.
    assert api.get("/users").status_code == 200


def test_admin_deleting_a_profile_removes_its_account(api):
    buyer = register_customer(api)
    seller = register_seller(api)
    admin = login_admin(api)
    add_product(seller)

    assert admin.delete(f"/customers/{buyer.customer_id}").status_code == 204
    assert api.post("/auth/login", json={"email": "buyer@test.local", "password": "buyer-password"}).status_code == 401
    assert buyer.get("/customer/profile").status_code == 404
    # A seller with products is still protected by the products foreign key.
    assert admin.delete(f"/sellers/{seller.seller_id}").status_code == 409


def test_profile_email_change_moves_the_login(api):
    buyer = register_customer(api)
    register_seller(api, email="taken@test.local")

    conflict = buyer.patch("/customer/profile", json={"email": "taken@test.local"})
    assert conflict.status_code == 409

    updated = buyer.patch("/customer/profile", json={"email": "New@Test.Local", "phone": "+77779999999"})
    assert updated.status_code == 200
    assert updated.json()["email"] == "new@test.local"
    assert updated.json()["phone"] == "+77779999999"
    assert updated.json()["full_name"] == "Aigerim Buyer"

    assert api.post("/auth/login", json={"email": "buyer@test.local", "password": "buyer-password"}).status_code == 401
    assert api.post("/auth/login", json={"email": "new@test.local", "password": "buyer-password"}).status_code == 200


def test_delivery_address_management(api):
    buyer = register_customer(api)
    assert buyer.get("/customer/delivery-address").json() == {"delivery_address": "Almaty, Abay 1"}

    response = buyer.put("/customer/delivery-address", json={"delivery_address": "Astana, Mangilik El 5"})
    assert response.status_code == 200
    assert buyer.get("/customer/profile").json()["delivery_address"] == "Astana, Mangilik El 5"

    assert buyer.put("/customer/delivery-address", json={"delivery_address": ""}).status_code == 422
