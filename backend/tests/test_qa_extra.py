"""QA: 10 дополнительных API-тестов (FastAPI TestClient + PostgreSQL).

Запуск (из папки backend/):
    TEST_DATABASE_URL=postgresql://shop:shop@localhost:5432/shop_test python -m pytest tests/test_qa_extra.py -v

Фикстура `api` и хелперы берутся из conftest.py (БД чистится перед каждым тестом).
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from conftest import (
    add_product,
    login_admin,
    register_customer,
    register_seller,
)

REGISTER_URL = "/auth/register/customer"


# ---------------------------------------------------------------------------
# TC-01  Авторизация: граница длины пароля (boundary value analysis)
# ---------------------------------------------------------------------------
def test_tc01_password_length_boundary(api):
    base = {
        "full_name": "Test User",
        "phone": "+77010000000",
        "delivery_address": "Almaty, Abay 1",
    }

    # 7 символов — слишком коротко
    too_short = api.post(REGISTER_URL, json={**base, "email": "a@test.local", "password": "abc-123"})
    assert too_short.status_code == 422

    # 8 символов — минимально допустимо
    ok = api.post(REGISTER_URL, json={**base, "email": "b@test.local", "password": "abc-1234"})
    assert ok.status_code == 201

    # 128 символов — максимально допустимо, 129 — уже нет
    longest = api.post(REGISTER_URL, json={**base, "email": "c@test.local", "password": "x-" * 64})
    assert longest.status_code == 201
    too_long = api.post(REGISTER_URL, json={**base, "email": "d@test.local", "password": "x-" * 64 + "x"})
    assert too_long.status_code == 422


def test_password_requires_letter_and_special_character(api):
    base = {
        "full_name": "Test User",
        "phone": "+77010000000",
        "delivery_address": "Almaty, Abay 1",
    }
    no_letter = api.post(REGISTER_URL, json={**base, "email": "a@test.local", "password": "1234-5678"})
    assert no_letter.status_code == 422
    no_special = api.post(REGISTER_URL, json={**base, "email": "b@test.local", "password": "abcd1234"})
    assert no_special.status_code == 422
    seller = api.post(
        "/auth/register/seller",
        json={"email": "c@test.local", "password": "abcd1234", "store_name": "S", "phone": "1"},
    )
    assert seller.status_code == 422


# ---------------------------------------------------------------------------
# TC-02  Безопасность: подделанный и просроченный JWT-токен
# ---------------------------------------------------------------------------
def test_tc02_tampered_and_expired_tokens_are_rejected(api):
    from app.core.config import JWT_ALGORITHM, JWT_SECRET

    buyer = register_customer(api)
    claims = {"sub": str(buyer.account_id), "role": "customer", "customer_id": buyer.customer_id}

    def me(token):
        return api.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    # Контроль: настоящий токен работает
    assert me(buyer.token).status_code == 200

    # Токен, подписанный чужим секретом
    forged = jwt.encode({**claims, "exp": datetime.now(UTC) + timedelta(hours=1)},
                        "wrong-secret-wrong-secret-1234567890", algorithm=JWT_ALGORITHM)
    assert me(forged).status_code == 401

    # Правильная подпись, но срок действия истёк
    expired = jwt.encode({**claims, "exp": datetime.now(UTC) - timedelta(minutes=1)},
                         JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert me(expired).status_code == 401

    # Токен без обязательного поля exp
    no_exp = jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)
    assert me(no_exp).status_code == 401

    # Токен с алгоритмом none (классическая атака)
    none_alg = jwt.encode({**claims, "exp": datetime.now(UTC) + timedelta(hours=1)},
                          key=None, algorithm="none")
    assert me(none_alg).status_code == 401


# ---------------------------------------------------------------------------
# TC-03  Корзина: невалидные входные данные
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload, expected", [
    ({"product_id": 1, "quantity": 0}, 422),        # количество 0
    ({"product_id": 1, "quantity": -5}, 422),       # отрицательное
    ({"product_id": 1, "quantity": 10_001}, 422),   # больше максимума
    ({"product_id": 0, "quantity": 1}, 422),        # id должен быть > 0
    ({"product_id": 1, "quantity": "много"}, 422),  # не число
    ({"quantity": 1}, 422),                         # нет product_id
    ({"product_id": 999_999, "quantity": 1}, 404),  # товара не существует
])
def test_tc03_cart_rejects_invalid_input(api, payload, expected):
    buyer = register_customer(api)
    response = buyer.post("/customer/cart/items", json=payload)
    assert response.status_code == expected, response.text
    # Что бы ни случилось, корзина осталась пустой
    assert buyer.get("/customer/cart").json()["items"] == []


# ---------------------------------------------------------------------------
# TC-04  Корзина: количество суммируется, превышение остатка отклоняется
# ---------------------------------------------------------------------------
def test_tc04_cart_accumulates_quantity_and_respects_stock(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    product = add_product(seller, name="Mouse", price="10.00", stock=5)
    url = "/customer/cart/items"
    pid = product["product_id"]

    assert buyer.post(url, json={"product_id": pid, "quantity": 3}).status_code == 200
    # Тот же товар ещё раз: 3 + 3 = 6 > 5, должна быть ошибка бизнес-правила
    over = buyer.post(url, json={"product_id": pid, "quantity": 3})
    assert over.status_code == 400
    assert "Not enough stock" in over.json()["detail"]

    # Корзина не изменилась: одна позиция, количество 3
    cart = buyer.get("/customer/cart").json()
    assert [(i["product_id"], i["quantity"]) for i in cart["items"]] == [(pid, 3)]

    # Докладываем ровно до остатка: 3 + 2 = 5 — разрешено
    cart = buyer.post(url, json={"product_id": pid, "quantity": 2}).json()
    assert cart["items"][0]["quantity"] == 5
    assert cart["total_amount"] == "50.00"
    assert cart["can_checkout"] is True


# ---------------------------------------------------------------------------
# TC-05  Каталог: валидация пагинации и сортировки
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("params", [
    {"limit": 0},
    {"limit": 101},
    {"limit": -1},
    {"offset": -1},
    {"sort": "cheapest"},
    {"seller_id": 0},
    {"search": "x" * 151},
])
def test_tc05_catalog_rejects_invalid_query_params(api, params):
    assert api.get("/catalog/products", params=params).status_code == 422


def test_tc05b_catalog_pagination_slices_results(api):
    seller = register_seller(api)
    for n in range(1, 6):
        add_product(seller, name=f"Item {n}", price=f"{n}.00", stock=1)

    page1 = api.get("/catalog/products", params={"limit": 2, "offset": 0}).json()
    page2 = api.get("/catalog/products", params={"limit": 2, "offset": 2}).json()
    page3 = api.get("/catalog/products", params={"limit": 2, "offset": 4}).json()
    beyond = api.get("/catalog/products", params={"limit": 2, "offset": 100}).json()

    names = [p["product_name"] for p in page1 + page2 + page3]
    assert names == [f"Item {n}" for n in range(1, 6)]  # без дублей и пропусков
    assert [len(page1), len(page2), len(page3)] == [2, 2, 1]
    assert beyond == []


# ---------------------------------------------------------------------------
# TC-06  Продавец: валидация данных товара (цена, название, остаток)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload", [
    {"product_name": "A", "price": "-1.00", "stock_quantity": 1},        # отрицательная цена
    {"product_name": "A", "price": "10.999", "stock_quantity": 1},       # 3 знака после запятой
    {"product_name": "A", "price": "100000000.00", "stock_quantity": 1}, # больше 10 цифр
    {"product_name": "", "price": "10.00", "stock_quantity": 1},         # пустое название
    {"product_name": "A" * 151, "price": "10.00", "stock_quantity": 1},  # слишком длинное название
    {"product_name": "A", "price": "10.00", "stock_quantity": -1},       # отрицательный остаток
    {"product_name": "A", "price": "abc", "stock_quantity": 1},          # цена не число
    {"product_name": "A", "stock_quantity": 1},                          # нет цены
])
def test_tc06_seller_cannot_create_invalid_product(api, payload):
    seller = register_seller(api)
    assert seller.post("/seller/products", json=payload).status_code == 422
    assert seller.get("/seller/products").json() == []


def test_tc06b_free_product_with_zero_stock_is_allowed(api):
    """Граничное значение: цена 0.00 и остаток 0 допустимы по схеме."""
    seller = register_seller(api)
    product = add_product(seller, name="Freebie", price="0.00", stock=0)
    card = api.get(f"/catalog/products/{product['product_id']}").json()
    assert card["price"] == "0.00"
    assert card["in_stock"] is False


# ---------------------------------------------------------------------------
# TC-07  Заказ: покупка всего остатка → товар заканчивается
# ---------------------------------------------------------------------------
def test_tc07_buying_all_stock_marks_product_out_of_stock(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    other = register_customer(api, email="other@test.local")
    admin = login_admin(api)
    product = add_product(seller, name="Last one", price="50.00", stock=2)
    pid = product["product_id"]

    buyer.post("/customer/cart/items", json={"product_id": pid, "quantity": 2})
    assert buyer.post("/customer/orders", json={}).status_code == 201

    card = api.get(f"/catalog/products/{pid}").json()
    assert card["stock_quantity"] == 0
    assert card["in_stock"] is False

    in_stock_ids = [p["product_id"] for p in api.get("/catalog/products", params={"in_stock": True}).json()]
    assert pid not in in_stock_ids

    # Другой покупатель уже не может положить товар в корзину
    assert other.post("/customer/cart/items", json={"product_id": pid}).status_code == 400

    # Админская аналитика видит товар как закончившийся
    assert admin.get("/admin/analytics/summary").json()["products"]["out_of_stock"] == 1


# ---------------------------------------------------------------------------
# TC-08  Заказ: сумма заказа не может превышать NUMERIC(10, 2)
# ---------------------------------------------------------------------------
def test_tc08_order_total_over_limit_is_rejected_and_stock_untouched(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    product = add_product(seller, name="Gold bar", price="99999999.99", stock=5)
    pid = product["product_id"]

    # Ровно на границе: один товар = 99 999 999.99 — проходит
    buyer.post("/customer/cart/items", json={"product_id": pid, "quantity": 1})
    ok = buyer.post("/customer/orders", json={})
    assert ok.status_code == 201
    assert ok.json()["total_amount"] == "99999999.99"

    # Два товара — выше границы: 400 вместо 500 и без списания остатка
    buyer.post("/customer/cart/items", json={"product_id": pid, "quantity": 2})
    too_much = buyer.post("/customer/orders", json={})
    assert too_much.status_code == 400
    assert "maximum" in too_much.json()["detail"].lower()

    assert api.get(f"/catalog/products/{pid}").json()["stock_quantity"] == 4   # 5 - 1, второй заказ не прошёл
    assert len(buyer.get("/customer/orders").json()) == 1
    assert buyer.get("/customer/cart").json()["items"][0]["quantity"] == 2     # корзина сохранилась


# ---------------------------------------------------------------------------
# TC-09  Заказ: отменённый заказ нельзя оплатить ни покупателем, ни админом
# ---------------------------------------------------------------------------
def test_tc09_cancelled_order_cannot_be_paid(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    admin = login_admin(api)
    product = add_product(seller, name="Lamp", price="20.00", stock=3)

    buyer.post("/customer/cart/items", json={"product_id": product["product_id"], "quantity": 1})
    order = buyer.post("/customer/orders", json={}).json()   # payment_status = pending
    oid = order["order_id"]

    cancelled = buyer.post(f"/customer/orders/{oid}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["order_status"] == "cancelled"
    assert cancelled.json()["payment_status"] == "pending"   # не оплачен → возврата нет

    pay = buyer.post(f"/customer/orders/{oid}/pay")
    assert pay.status_code == 400
    assert "cancelled" in pay.json()["detail"].lower()

    admin_pay = admin.patch(f"/admin/orders/{oid}/payment-status", json={"payment_status": "paid"})
    assert admin_pay.status_code == 400

    # Статус заказа так и остался pending
    assert buyer.get(f"/customer/orders/{oid}").json()["payment_status"] == "pending"


# ---------------------------------------------------------------------------
# TC-10  Заказ: точность денежных расчётов (Decimal, без ошибок float)
# ---------------------------------------------------------------------------
def test_tc10_money_calculations_are_exact(api):
    seller = register_seller(api)
    buyer = register_customer(api)
    cheap = add_product(seller, name="Sticker", price="0.10", stock=100)
    odd = add_product(seller, name="Cable", price="19.99", stock=100)

    # float: 0.1 * 3 = 0.30000000000000004 — у нас должно быть ровно 0.30
    buyer.post("/customer/cart/items", json={"product_id": cheap["product_id"], "quantity": 3})
    buyer.post("/customer/cart/items", json={"product_id": odd["product_id"], "quantity": 3})

    cart = buyer.get("/customer/cart").json()
    assert {i["product_id"]: i["subtotal"] for i in cart["items"]} == {
        cheap["product_id"]: "0.30",
        odd["product_id"]: "59.97",
    }
    assert cart["total_amount"] == "60.27"

    order = buyer.post("/customer/orders", json={"payment_status": "paid"}).json()
    assert order["total_amount"] == "60.27"
    assert sum(float(i["subtotal"]) for i in order["items"]) == pytest.approx(60.27)

    admin = login_admin(api)
    summary = admin.get("/admin/analytics/summary").json()["orders"]
    assert summary["paid_revenue"] == "60.27"
    assert summary["average_paid_order"] == "60.27"
