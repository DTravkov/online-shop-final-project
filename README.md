# Online Shop

FastAPI backend and React + Vite frontend, with PostgreSQL and Redis, using
Docker Compose.

## Application structure

```text
backend/
  app/
    api/          # HTTP routes
    service/      # Application operations and transaction boundaries
    repository/   # Database queries
    models/       # SQLAlchemy models
    schemas/      # Pydantic request and response schemas
    core/         # Configuration and database session
    exceptions/   # Plain application exceptions
    utils/        # Reserved for small shared helpers
    main.py       # Application setup, lifespan, exception mapping, health check
  requirements.txt     # Backend runtime dependencies
  requirements-dev.txt # Backend development dependencies
  Dockerfile           # Python API image
  .dockerignore        # Backend build context exclusions
front/
  src/          # React entry point, app component, and styles
  index.html    # HTML entry point
  vite.config.js # Dev server and API proxy
  Dockerfile    # Node.js frontend image
compose.yaml    # Shared stack configuration
.env.example    # Shared Compose environment example
```

`backend/` and `front/` are separate Docker build contexts. Backend Python
commands run from `backend/`, where `app/` remains the application package;
imports such as `from app.main import app` are unchanged. Run Compose commands
from the repository root. Shared environment configuration and documentation
also stay in the root.

Dependencies flow `router -> service -> repository -> database` using
FastAPI `Depends`. Each request gets an async SQLAlchemy session, closed after
the request. Services define write transaction boundaries using the repository's
transaction context: success commits and exceptions roll back. Repository writes
only flush changes, so multiple writes can share one service transaction. Services return
Pydantic schemas and raise plain exceptions; the application maps missing records
to HTTP 404, database integrity conflicts to HTTP 409, authentication failures to
401, role violations to 403, and business rule violations to 400. There are no
generic base repositories or service abstractions.

The example user has an integer `id` and a `name` (1–100 characters):

- `POST /users` — create with `{"name": "Alice"}`
- `GET /users?offset=0&limit=20` — list (maximum 100 per request)
- `GET /users/{user_id}` — read
- `PUT /users/{user_id}` — replace the name
- `DELETE /users/{user_id}` — delete, returning HTTP 204

SQLAlchemy models define the database schema. Missing tables are created on
startup, including the timezone-aware order date column. Existing table
definitions are not changed by startup (see
[Upgrading an existing database](#upgrading-an-existing-database)). The example
user is independent of marketplace accounts and has no authentication.

## Accounts and authentication

Customers and sellers register themselves; each registration creates a profile
(`customers` or `sellers` row) and an `accounts` row holding the login email,
a scrypt password hash, and the role (`customer`, `seller`, or `admin`). Emails
are trimmed, lowercased, and unique across all accounts.

Registration and login return a JWT access token. Send it on every protected
request:

```text
Authorization: Bearer <access_token>
```

In Swagger UI, press **Authorize** and paste the token. Tokens are signed with
`JWT_SECRET` and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440).
Administrators cannot self-register: when `ADMIN_EMAIL` and `ADMIN_PASSWORD`
are set, startup creates that administrator account if it is missing. Compose
defaults them to `admin@shop.local` / `admin12345` for local development.

Missing or invalid tokens return 401; a valid token with the wrong role returns
403.

## Marketplace API

| Method | Path | Who | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register/customer` | anyone | Create a customer account (full name, email, phone, delivery address, password) |
| POST | `/auth/register/seller` | anyone | Create a seller account (store name, email, phone, password); rating starts at 0.0 |
| POST | `/auth/login` | anyone | Exchange email and password for a token |
| GET | `/auth/me` | signed in | Current account |
| GET | `/catalog/products` | anyone | Catalog: `search` (name, case-insensitive), `seller_id`, `in_stock`, `sort` (`id`, `price_asc`, `price_desc`, `name`), `offset`, `limit` |
| GET | `/catalog/products/{product_id}` | anyone | Product card: name, price, stock, seller, and `offers` from every seller of the same product name |
| GET, PATCH | `/customer/profile` | customer | View or edit full name, email, phone |
| GET, PUT | `/customer/delivery-address` | customer | Default delivery address |
| GET | `/customer/cart` | customer | Cart with items, availability, and totals |
| POST | `/customer/cart/items` | customer | Add a product (`product_id`, `quantity`); repeats increase the quantity |
| PUT, DELETE | `/customer/cart/items/{product_id}` | customer | Set the quantity or remove the item |
| DELETE | `/customer/cart` | customer | Empty the cart |
| POST | `/customer/orders` | customer | Checkout: optional `delivery_address`, `payment_status` `pending` (default) or `paid` |
| GET | `/customer/orders` | customer | Order history with items, newest first; optional `order_status` filter |
| GET | `/customer/orders/{order_id}` | customer | One order with order and payment status |
| POST | `/customer/orders/{order_id}/pay` | customer | Simulated payment: `pending` → `paid` |
| POST | `/customer/orders/{order_id}/cancel` | customer | Cancel a `new` order |
| GET, PATCH | `/seller/profile` | seller | Store profile with rating; edit store name, email, phone |
| GET, POST | `/seller/products` | seller | Own products (`include_inactive` to show withdrawn ones); add a product |
| GET, PATCH, DELETE | `/seller/products/{product_id}` | seller | View, edit (name, price, stock, `is_active`), or withdraw from sale |
| GET | `/seller/orders` | seller | Orders containing the seller's products; optional `order_status` filter |
| GET | `/seller/orders/{order_id}` | seller | One such order with only the seller's items |
| PATCH | `/seller/orders/{order_id}/status` | seller | Move the order to `shipped` or `delivered` |
| GET | `/admin/analytics/top-products` | admin | Best sellers by units (`limit`, default 5) |
| GET | `/admin/analytics/summary` | admin | Counts of users, products, and orders by status; items sold; paid revenue |
| GET | `/admin/orders` | admin | All orders; `order_status` and `payment_status` filters |
| GET | `/admin/orders/{order_id}` | admin | One order with items |
| PATCH | `/admin/orders/{order_id}/payment-status` | admin | Change the payment status |

Business errors such as insufficient stock or a forbidden status change return
400 with a `detail` message.

### Business rules

- **Cart.** Only active products can be added. The quantity in the cart cannot
  exceed the current stock. Withdrawn products are removed from every cart.
- **Checkout.** One checkout creates one order for the whole cart, even when it
  contains several sellers' products. Within one transaction it locks the
  products, checks availability, stores each item's current price as
  `unit_price`, computes `total_amount`, reduces stock, and empties the cart.
  Concurrent checkouts cannot oversell. The order starts as `new`; the delivery
  address defaults to the customer's profile address.
- **Order status.** A seller whose products are in the order may change its
  status: `new` → `shipped`, `new` → `delivered`, `shipped` → `delivered`. The
  status is shared by the whole order. A customer may cancel only a `new`
  order; cancelling returns the stock and turns a `paid` order into `refunded`.
- **Payment status.** Customers can pay a `pending` order. Administrators may
  change `pending` → `paid` and `paid` → `refunded`. A cancelled order cannot
  become paid.
- **Products.** Sellers manage only their own products. Deleting a product
  withdraws it from sale (`is_active = false`); it stays in order history and
  can be returned to sale with `is_active: true`. Sellers cannot change their
  rating.
- **Analytics.** Top products and items sold ignore cancelled and refunded
  orders. Paid revenue sums paid, non-cancelled orders.

## Table CRUD

Each table also has raw CRUD routes. They bypass the business rules above, so
they **require an administrator token**:

| Resource | Base path | Primary key |
| --- | --- | --- |
| Customers | `/customers` | `customer_id` |
| Sellers | `/sellers` | `seller_id` |
| Products | `/products` | `product_id` |
| Orders | `/orders` | `order_id` |
| Order items | `/order-items` | `order_item_id` |

All support `POST` and paginated `GET` on the base path, plus `GET`, `PUT`, and
`DELETE` on `/{primary_key}`. Creates return 201; deletes return 204. Lists use
`offset=0&limit=20` by default, with a maximum limit of 100. PUT replaces all
writable fields; callers supply prices, totals, stock, dates, and statuses, and
nothing is recalculated.

Foreign keys must reference existing records. Deleting a referenced parent
returns 409; delete dependent records first. Deleting a customer or seller also
deletes its account and cart. Failed writes roll back.

Order dates must include a timezone: for example,
`"order_date": "2026-11-05T10:31:56.731Z"` or
`"order_date": "2026-11-05T15:31:56.731+05:00"`. PostgreSQL stores the instant
using `TIMESTAMP WITH TIME ZONE`; the original offset is not retained. Dates
without a timezone return HTTP 422.

## Upgrading an existing database

New tables (`accounts`, `cart_items`) are created automatically. Two columns
were added to existing tables, which startup does not alter. Either recreate the
local database (this deletes its data):

```sh
docker compose down -v
docker compose up --build
```

or keep the data and add the columns:

```sh
docker compose exec postgres psql -U shop -d shop -c "ALTER TABLE products ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE; ALTER TABLE orders ADD COLUMN delivery_address VARCHAR(255);"
```

## Tests

From `backend/`, with the development dependencies installed
(`pip install -r requirements-dev.txt`):

```sh
TEST_DATABASE_URL=postgresql://shop:shop@localhost:5432/shop_test python -m pytest
```

API tests need an empty PostgreSQL database that they can wipe; without
`TEST_DATABASE_URL` they are skipped and only schema tests run. With the Compose
stack running, create one with
`docker compose exec postgres createdb -U shop shop_test`.

## Run

Install Docker with the Compose plugin, then copy the example environment file:

```sh
cp .env.example .env
```

On PowerShell:

```powershell
Copy-Item .env.example .env
```

Start all services (frontend, API, PostgreSQL, and Redis):

```sh
docker compose up
```

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Compose builds missing images on the first run. Use `docker compose up --build`
after changing dependencies or a Dockerfile (PyJWT was added for authentication), and add `-d` to run in the background.
`docker-compose up` also works where the standalone Compose command is installed.
Set `FRONT_PORT` or `API_PORT` in `.env` to change the published ports.

Both applications reload during development: Python changes under `backend/app/`
restart Uvicorn, and changes under `front/src/` update through Vite. The frontend's
`index.html` and `vite.config.js` are also mounted into its container. Polling is
enabled for frontend file watching in Docker, including on Windows. Frontend
dependencies stay inside the image; rebuild it after changing `package.json`
or `package-lock.json`.

The health endpoint checks both PostgreSQL and Redis and returns HTTP 503 if either is unavailable. PostgreSQL and Redis data persist in Docker volumes. The frontend and API ports are published to the host.

The example credentials are for local development. Use a URL-safe password in `.env` because it is included in the database connection URL.

Stop the services:

```sh
docker compose down
```

## Frontend

`front/` contains a minimal React + Vite JavaScript app with a startup screen.
There are no marketplace pages or client-side routes yet. Its Docker image uses
Node.js 24.

For future API calls, use relative URLs such as `fetch('/api/products')`.
Vite removes the `/api` prefix and forwards the request to `http://api:8000`
inside Compose, so browser requests use the frontend's origin.

To run the frontend outside Docker, use Node.js 20.19+ or 22.12+:

```sh
cd front
npm ci
npm run dev
```

On PowerShell, use `npm.cmd` if execution policy blocks `npm.ps1`.
The local proxy defaults to `http://localhost:8000`; set `API_PROXY_TARGET`
in the shell environment if the API runs elsewhere.

`npm run build` generates static assets in `front/dist/`, and `npm run preview`
serves that build locally. Vite also uses the proxy during local preview. The
static assets do not include an API proxy; a production deployment will need
its own API routing.
