# Mint Market

A small marketplace built with React, FastAPI, PostgreSQL, and Redis.
Customers can shop from several sellers in one checkout. Each seller handles
its own delivery, and buyers can review a shop after receiving a paid purchase.

## What works today

- Public catalog with search, sorting, stock filters, and seller offers.
- Public shop pages with available products, average ratings, and buyer comments.
- Customer and seller registration, login, and profile editing.
- A persistent cart, checkout, order history, balance payments, and cancellation.
- Personal balances, free test deposits, seller revenue, and transaction history.
- Seller product management and independent delivery status for each shop.
- Optional Telegram alerts for new seller orders and customer order status changes.
- Administrator APIs for payments, analytics, and direct table management.

The interface is in Russian, with prices displayed in tenge (KZT). Product visuals
are generated from names; there are no product photo uploads. Payments are a
simulation, and there is no administrator dashboard yet.

## Start with Docker

From the repository root, copy the example settings and start the stack:

```sh
cp .env.example .env
docker compose up --build
```

In PowerShell, use `Copy-Item .env.example .env` instead of `cp`.

| Service | Address |
| --- | --- |
| Marketplace | http://localhost:5173 |
| API documentation (Swagger) | http://localhost:8000/docs |
| API health check | http://localhost:8000/health |

Compose runs Python 3.12, Node.js 24, PostgreSQL 17, and Redis 7. Source files are
mounted for automatic reload. Rebuild after dependency or Dockerfile changes.
Use `docker compose up -d` for background operation and `docker compose down`
to stop; database data stays in Docker volumes.

`.env.example` lists development settings. `FRONT_PORT` and `API_PORT` change the
published ports. Replace the development JWT secret and credentials before
exposing the app. The default administrator is `admin@shop.local` / `admin12345`.
Startup creates it only if that email is unused; changing the password setting
does not update an existing account.

The backend reads process environment variables, not `.env` directly. Compose
passes database/Redis URLs, JWT secret, and administrator settings to the API.
`ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 1440 when running the backend.

## Deploy on Vercel

Import the repository with root directory `./` and application preset **Services**.
The root `vercel.json` sends `/api` and `/api/*` to FastAPI and serves the Vite
site on the same domain. Keep **Automatically expose System Environment Variables**
enabled so the backend receives `VERCEL=1` and uses `/api` as its root path.

Set these project environment variables before deploying. Use separate
databases and secrets for production and preview deployments.

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection URI reachable from Vercel, for example `postgresql://USER:PASSWORD@HOST/DB?ssl=require`. |
| `REDIS_URL` | Redis connection URI reachable from Vercel. Use `rediss://` when your provider requires TLS. |
| `JWT_SECRET` | A unique, randomly generated signing secret. |
| `ADMIN_EMAIL` and `ADMIN_PASSWORD` | Optional credentials for creating an administrator on first startup. |

After deployment, open `/` for the storefront, `/api/docs` for Swagger, and
`/api/health` to check PostgreSQL and Redis connectivity.

## Telegram notifications

Create a bot in [BotFather](https://t.me/BotFather), then set the Telegram values
from `.env.example`. Use a separate bot and secrets for each environment.
Generate three independent Base64URL values by running this command three times
for `TELEGRAM_START_KEY`, `TELEGRAM_BOT_KEY`, and `TELEGRAM_SERVICE_TOKEN`.

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

| Variable | Service | Value |
| --- | --- | --- |
| `TELEGRAM_BOT_USERNAME` | FastAPI | Bot username without `@`. Leave empty to disable the integration. |
| `TELEGRAM_START_KEY` | FastAPI | Secret that encrypts the short reference in each website link. |
| `TELEGRAM_BOT_KEY` | FastAPI and bot | Shared encryption key for private-chat redemption requests. |
| `TELEGRAM_SERVICE_TOKEN` | FastAPI and bot | Shared bearer credential for bot-only API requests. |
| `TELEGRAM_BOT_TOKEN` | Bot | Bot API token from BotFather. |
| `TELEGRAM_BACKEND_URL` | Bot | FastAPI base URL. Compose sets `http://api:8000`. For Vercel use `https://YOUR_DOMAIN/api`. |

Start the stack with `docker compose --profile telegram up --build`. For Vercel,
deploy the `telegram-bot/` Docker image as one always-on replica and configure
its environment separately. The bot uses outbound HTTPS and needs no inbound
port. FastAPI creates the Telegram tables on startup in the existing database.

From a customer or seller profile, choose **Подключить Telegram**, open the bot
and press **Start**, then enter its confirmation code in the same website
profile. Each link expires after five minutes and can be redeemed once. Select
**Отключить Telegram** to stop new order notifications. Messages already queued,
including the unlink confirmation, remain deliverable to their original chat.
Each notification stores the chat ID at enqueue time, independently of the
account link. Relinking does not redirect old messages to the new chat, and
delivery and retries remain ordered per chat even across link changes.

Sellers get one message per new order containing their products, including
orders awaiting payment. Customers get a message when the overall delivery
status changes, including partial progress and cancellation. FastAPI commits
jobs with the order change and the bot retries temporary delivery failures.

## Using the marketplace

Browse products without signing in. Click a shop name on a product or order to
open its public page. Shop URLs look like `http://localhost:5173/#/shops/1` and
can be shared or refreshed. Shop products and reviews have pagination.

Create a customer account to add products to a cart and check out. One checkout
creates one order, snapshots prices, reserves stock, and empties the cart. You
can use your saved address or enter another address, and pay now or later.
Open **Balance** to add test money to your account. Any signed-in customer, seller,
or administrator can deposit a positive amount without a bank or payment provider.
Balances start at zero. Amounts use up to two decimal places; the storage limit is
999,999,999,999.99 KZT. These are testing funds, not real money.

Paying debits the buyer's balance and immediately credits each seller for their
own products at the order's saved prices. There are no platform fees. Insufficient
funds leave a pending order unpaid; a failed pay-now checkout also rolls back its
stock reservation and keeps the cart intact. You can top up and try again.
The Balance page shows deposits, purchases, seller revenue, and refunds.

An order has a separate delivery status for every seller. Sellers can move their
own part from `new` to `shipped` or `delivered`, then `shipped` to `delivered`.
The buyer sees each shop's progress and an overall summary:

| Seller progress | Overall order status |
| --- | --- |
| Every part is new | `new` |
| Some shipped, others still new | `partially_shipped` |
| Every part shipped | `shipped` |
| Some delivered, others not yet delivered | `partially_delivered` |
| Every part delivered | `delivered` |
| Customer cancelled before any seller progressed | `cancelled` |

You can cancel only while every part is new. Cancellation restores stock and
changes a paid order to refunded, returning funds to the buyer and reversing the
original seller payouts. Administrator refunds use the same transfers. A refund
never credits the buyer twice. Payment belongs to the whole order. Sellers
cannot mark another shop's products as sent or delivered.

After a seller's part is delivered and the order is paid, open that shop to leave
1-5 stars and a comment. You can have one review per shop, edit it, or delete it.
Comments are trimmed and limited to 2000 characters. The shop rating is the
average of its reviews, rounded to one decimal; a shop without reviews shows
0.0. Other shops in the same order do not need to finish delivery first.
Cancelled, unpaid, or refunded purchases do not qualify for creating/editing a
review. Existing reviews remain visible after a later refund.

Sellers can add/edit listings, change stock and prices, and withdraw products.
Withdrawal removes products from the public catalog and carts while preserving
order history. A withdrawn listing can be published again.

## API guide

Registration/login return a JWT. Protected requests use
`Authorization: Bearer <access_token>`; in Swagger, click **Authorize** and paste
the token. The browser stores its session in localStorage.

| Area | Main endpoints |
| --- | --- |
| Authentication | `POST /auth/register/customer`, `POST /auth/register/seller`, `POST /auth/login`, `GET /auth/me` |
| Balance (all signed-in roles) | `GET /wallet`, `POST /wallet/deposit`, `GET /wallet/transactions` |
| Catalog | `GET /catalog/products`, `GET /catalog/products/{product_id}` |
| Public shops | `GET /catalog/sellers/{seller_id}`, `GET /catalog/sellers/{seller_id}/reviews` |
| Customer profile | `GET/PATCH /customer/profile`, `GET/PUT /customer/delivery-address` |
| Cart | `GET/DELETE /customer/cart`, `POST /customer/cart/items`, `PUT/DELETE /customer/cart/items/{product_id}` |
| Customer orders | `POST/GET /customer/orders`, `GET /customer/orders/{order_id}`, `POST .../{order_id}/pay`, `POST .../{order_id}/cancel` |
| Own seller review | `GET/PUT/DELETE /customer/sellers/{seller_id}/review` |
| Seller cabinet | `GET/PATCH /seller/profile`, `GET/POST /seller/products`, `GET/PATCH/DELETE /seller/products/{product_id}` |
| Seller orders | `GET /seller/orders`, `GET /seller/orders/{order_id}`, `PATCH /seller/orders/{order_id}/status` |
| Administrator | `GET /admin/analytics/summary`, `GET /admin/analytics/top-products`, `GET /admin/orders`, `GET /admin/orders/{order_id}`, `PATCH /admin/orders/{order_id}/payment-status` |

Catalog filters: `search`, `seller_id`, `in_stock`, and `sort` (`id`, `price_asc`,
`price_desc`, `name`). Lists generally accept `offset=0&limit=20`, maximum 100.
The main catalog UI currently displays up to 48 results; cabinet lists show the
first 20. The shop page provides pagination for its products and comments.

Customer/admin order details include `items` and `fulfillments`. Seller order
responses contain only that seller's items: `order_status` is its own delivery
status, and `overall_order_status` is the whole order's summary. The seller list's
`order_status` filter also applies only to that seller. Update with a body such
as `{"order_status":"shipped"}`. Administrator payment transitions are
`pending -> paid -> refunded`.

Deposit with `POST /wallet/deposit` and a body such as `{"amount":"1000.50"}`.
`GET /wallet` returns the current balance and `currency: "KZT"`; transaction history
supports `offset`/`limit` and belongs only to the signed-in account. `/auth/me` also
includes the current balance. Duplicate order payments/refunds are rejected.
Raw CRUD changes do not move money; a later wallet payment requires valid order
items whose totals match and sellers with accounts. A raw paid flag without a
wallet payment cannot be refunded to a balance.

To save a review, PUT `{"rating":5,"comment":"Great service"}` to the own-review
endpoint. GET returns `can_review` and the buyer's existing `review` (or null).
Public reviews show the buyer's name, stars, comment, and timestamps.

Direct table CRUD is administrator-only at `/customers`, `/sellers`, `/products`,
`/orders`, and `/order-items`. Each supports POST/list GET and GET/PUT/DELETE by
ID. POST returns 201, DELETE 204, and PUT requires all writable fields. These
routes bypass marketplace calculations and balance transfers: orders/items are independent, and raw
writes do not generate seller fulfillments. `/users` is a public example table,
not an authentication resource. Accounts and orders with wallet history cannot
be deleted through table CRUD, preserving the transaction record.

Errors use JSON `detail`: 400 for business rules, 401 for missing/invalid tokens,
403 for permissions, 404 for missing records, 409 for foreign-key/uniqueness
conflicts, and 422 for invalid input. Order dates require `Z` or a UTC offset.
Monetary API fields use exact decimal values, usually serialized as strings.
See Swagger for complete request/response schemas.

## Code structure

```text
backend/app/
  api/ -> service/ -> repository/ -> PostgreSQL
  models/       SQLAlchemy tables
  schemas/      Pydantic validation and response shapes
  core/         Settings, sessions, security
  main.py       App startup, routes, error handling, health
backend/tests/  Schema and API integration tests
front/src/
  pages/        Customer/seller screens, public shops, and balances
  components/   Shared UI
  App.jsx       Session and hash navigation
  api.js        Requests to /api and formatting
compose.yaml    Local services and reload configuration
.github/        CI and Dependabot
```

Services own transactions; repositories flush without committing. A request
shares one async database session. Checkout locks stock, seller status changes
lock the parent order, and review writes lock the shop before updating its rating.
Wallet transfers lock all participating accounts by ID; ledger entries preserve
original payouts for refunds. PostgreSQL stores accounts and balances, profiles,
products, carts, orders, fulfillments, reviews, and wallet transactions. Redis
currently only participates in `/health`.

## Database changes

Startup creates tables from the models but does not alter existing tables.
This version adds `fulfillments`, `seller_reviews`, and
`order_items.fulfillment_id`. Account balances and the `wallet_transactions` ledger
are also new. Apply schema changes by recreating the database;
there are no migrations at this stage.

`telegram_notifications` now stores a `BigInteger` `chat_id` snapshot instead of
the `link_id` foreign key. Existing tables require recreation before running
this version; startup does not convert the old notification schema.

For a fresh local stack, the following deletes **all PostgreSQL and Redis data**,
including existing accounts and orders:

```sh
docker compose down --volumes
docker compose up --build
```

## Local development and checks

Backend: use Python 3.12, install `backend/requirements-dev.txt`, and run commands
from `backend/`. Supply `DATABASE_URL`, `REDIS_URL`, and security settings in the
shell, then run `uvicorn app.main:app --reload`.

```sh
python -m pytest
ruff check .
```

API tests require `TEST_DATABASE_URL` pointing to a disposable PostgreSQL database;
they drop all its tables before every test. Without it, database tests skip.
With Compose running, create a test database using
`docker compose exec postgres createdb -U shop shop_test`; use connection details
reachable from the environment running pytest. Compose does not publish the
PostgreSQL port by default.

Frontend: use Node.js 20.19+ or 22.12+ and run from `front/`:

```sh
npm ci
npm run dev
npm run build
```

Use `npm.cmd` on PowerShell if needed. Vite forwards `/api` to
`API_PROXY_TARGET` (default `http://localhost:8000`, Compose `http://api:8000`).
`npm run preview` also uses the proxy, but exported static files do not; production
hosting must route `/api` to the backend itself.

GitHub Actions runs Ruff, tests with PostgreSQL/Redis, the frontend build, and
Docker image builds. Dependabot checks dependency updates weekly.
