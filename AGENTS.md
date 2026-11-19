# Working in this repository

## What this project is

Mint Market is a small marketplace with a React frontend and one FastAPI backend.
Customers browse shops, buy products, track deliveries, and review sellers.
Sellers manage their listings and fulfill their own part of each order.
Administrators use protected APIs for table management, payments, and analytics.
Payments use internal balances with free testing deposits; no bank is connected.
PostgreSQL stores application data and the Telegram outbox. Redis supports
health checks and short-lived Telegram linking attempts. Keep improvements outside
the requested scope as proposals.

## Where things live

```text
backend/
  app/
    api/          HTTP routes and request contracts
    service/      Business operations and transaction boundaries
    repository/   Async SQLAlchemy queries and persistence
    models/       Tables; register each model in models/__init__.py
    schemas/      Pydantic input and output models
    core/         Environment settings, database sessions, passwords, JWTs
    exceptions/   Plain application exceptions
    utils/        Small shared helpers
    main.py       App setup, lifespan, router and exception registration
  tests/          Schema tests and PostgreSQL integration tests
  requirements*.txt, ruff.toml, Dockerfile
front/
  src/
    pages/        Catalog, cart, orders, seller cabinet, profile, auth, shop, wallet
    components/   Shared UI
    App.jsx       Session, navigation, catalog state, modals, notifications
    api.js        Fetch wrappers and display formatting
    helpers.js    Product visuals and translated statuses
    index.css     Shared styles
  package.json, package-lock.json, vite.config.js, Dockerfile
telegram-bot/    Standalone TypeScript bot, package files, tests, and Dockerfile
compose.yaml, .env.example, README.md
.github/          CI and dependency updates
```

Backend, frontend, and the Telegram bot are separate Docker build contexts.
Keep shared setup and documentation at the root. Run Python commands from
`backend/`, npm commands from the corresponding package directory, and Compose
commands from the root. The backend package remains
`app`, with entry point `app.main:app`. Keep the existing singular `service`
and `repository` names and resource-specific classes.

## Backend conventions

The request flow is `router -> service -> repository -> AsyncSession -> database`.

- Routers declare paths, schemas, statuses, query validation, and dependencies.
  Inject services with `Annotated[..., Depends(...)]`; keep SQL out of handlers.
- Services enforce business rules and ownership, choose transactions, and return
  Pydantic read schemas using `model_validate`. Raise application exceptions.
- Repositories return ORM records. Writes flush (and refresh where needed),
  but never commit independently. Feature services can use several repositories.
- Schemas validate inputs; read schemas use `ConfigDict(from_attributes=True)`.
  Use `model_dump` for validated writes. Models use `Mapped` and `mapped_column`.
- Register new routers and exception handlers in `main.py`, and new models in
  `models/__init__.py`. Put dependency factories alongside their classes.

One request shares one session (`expire_on_commit=False`). Start the service's
write transaction **before any lookup**: a read starts an implicit transaction,
so calling `begin()` afterwards fails. Authentication dependencies validate JWTs
without a database query for this reason. A repository transaction commits on
success and rolls back on any exception, including errors after a flush.
Marketplace transaction contexts translate `IntegrityError` to `RecordConflict`.
The public example user repository is the simpler exception to this pattern.

Lock mutable rows inside transactions. Checkout locks the customer before reading
the cart and locks products by primary key. Fulfillment updates and cancellations
lock the parent order so concurrent sellers cannot lose aggregate status updates.
Review writes lock the seller and update its average rating in the same transaction.
Wallet transfers lock all participating accounts in primary-key order and refresh
existing ORM state while locking. Deposits, debits, credits, ledger entries, and
payment status must commit/roll back together. WalletService charge/refund helpers
run inside their calling order service transaction; they never begin another one.

Exception mapping: missing records -> 404, conflicts -> 409, authentication -> 401
with `WWW-Authenticate: Bearer`, permissions -> 403, business rules -> 400.
FastAPI validation errors return 422. Error bodies use `detail`.

## Marketplace rules to preserve

- `/auth`: customer/seller registration and login. Accounts contain normalized,
  unique email, scrypt password hash, JWT identity, role, and linked profile.
  Administrators are created at startup from environment settings.
- `/catalog`: public products, product offers, shop profiles, and buyer reviews.
  Listings of the same product are matched by trimmed, case-insensitive name.
- `/customer`: own profile, address, PostgreSQL cart, orders, payments, cancellation,
  and own seller review. `/seller`: own profile, listings, and fulfillments.
  `/admin`: analytics, all orders, and payment status management.
- Checkout creates one order with price snapshots and one `fulfillments` row per
  seller, reserves stock, and clears the cart atomically. Each marketplace order
  item links to its fulfillment, preserving the original seller.
- Sellers change only their own fulfillment: `new -> shipped/delivered` and
  `shipped -> delivered`. Seller API `order_status` and its list filter refer to
  that seller's status; `overall_order_status` describes the whole order.
- Customer/admin orders expose all `fulfillments`. Overall status is `new`,
  `partially_shipped`, `shipped`, `partially_delivered`, `delivered`, or `cancelled`.
  All seller parts must arrive before the whole order becomes delivered.
- Customers cancel only wholly new orders. Cancellation marks every fulfillment
  cancelled, restores stock, and refunds a paid order. Payment is order-wide:
  `pending -> paid -> refunded`. Customers pay from their balance; admins can charge/refund using the same flow.
- Every authentication account has a zero-initialized `Numeric(14, 2)` balance.
  `/wallet` and `/wallet/transactions` read only the signed-in account. Any role
  can POST `/wallet/deposit` with a positive test amount (up to two decimal places).
  Maximum balance is 999999999999.99 KZT; do not round invalid deposit inputs.
- Payment debits the customer and immediately credits each seller their item-price
  subtotal. Use the fulfillment's original seller, not a reassigned listing owner.
  Insufficient funds or any failure rolls back all participants and checkout state.
  Pending orders reserve stock without moving money. Refunds reverse the original
  `wallet_transactions` entries; never recalculate payouts from edited items.
  The ledger's unique account/order/kind constraint also prevents duplicate moves.
  Wallet history protects its accounts/orders from deletion. Raw table CRUD never
  moves balances; a paid flag alone cannot create a balance refund.
- Withdrawing a product sets `is_active=False`, removes it from carts, and keeps
  order history. Money uses `Decimal`/`Numeric`; order dates require a timezone.
- One review per customer/seller: 1-5 stars and a trimmed 1-2000 character comment.
  Creating/editing requires a paid, delivered fulfillment from that seller.
  Buyers can delete their own review. Ratings are averages rounded to one decimal;
  no reviews means 0.0. Public reviews expose buyer names, never login details.
- Admin-only table CRUD remains separate from marketplace rules: `/customers`,
  `/sellers`, `/products`, `/orders`, `/order-items`. `/users` is a public example,
  unrelated to accounts. CRUD PUT replaces all writable fields; POST returns 201,
  DELETE 204. Lists default to offset 0/limit 20, maximum 100. Raw CRUD does not
  create fulfillments or recalculate prices, stock, totals, ratings, or balances.
- Foreign keys reject invalid references and referenced-parent deletions with 409.
  Accounts/cart entries cascade with profiles; fulfillments cascade with orders.
  Order items must be removed before deleting an order. Reviews must be removed
  before deleting their customer/seller.

## Frontend conventions

The balance page supports deposits and paginated transaction history for every role.
Refresh displayed balances after deposits, payments, refunds, and page/focus changes.
Use React hooks and props; there is no routing/state library or StrictMode wrapper.
Navigation uses URL hashes; public shop links are `#/shops/{seller_id}` and work
on refresh and browser back/forward. Keep customer and seller workflows separate.
Session data and JWTs live in localStorage and are passed to `api.js` explicitly.
Customers and sellers link or unlink Telegram from their profile. Linking
requires a code received in a private bot chat. PostgreSQL enforces unique chat
IDs across accounts. Order transactions enqueue notifications for linked accounts.
Queued notifications store a snapshot of the destination chat ID, with no link
foreign key. Unlinking stops future order notifications but preserves queued jobs,
including the unlink confirmation. Delivery and retries stay ordered per chat ID,
even if that chat is later linked again.
The bot holds the Telegram API token and communicates with FastAPI over HTTP.

Use relative `/api/...` URLs. Vite strips `/api` and proxies to `API_PROXY_TARGET`
(default `http://localhost:8000`, Compose `http://api:8000`). The server listens
on `0.0.0.0:5173` with a strict port; `USE_POLLING=true` helps Docker file watching.
Vercel Services routes `/api` and its descendants to FastAPI using the root
`vercel.json`. On Vercel the backend uses the `/api` root path, while Compose
uses the unprefixed backend paths behind Vite's local proxy.
Preserve npm and the lockfile; rebuild images after dependency changes.

## Running and checking changes

See README for setup. Docker uses Python 3.12, Node.js 24, PostgreSQL 17, Redis 7.
Compose mounts backend app and frontend source for reload. Settings come from the
process environment; the app does not read `.env` itself. Startup calls
`Base.metadata.create_all`; schema changes are applied by recreating the database.
Do not add migrations or upgrade SQL for this stage. Never reset user data unless
explicitly asked. Keep credentials, virtual environments, caches, and build output
out of Git.

Backend checks (Python 3.12, development requirements installed):

```sh
python -m pytest
ruff check .
```

API tests require `TEST_DATABASE_URL` pointing to a disposable PostgreSQL database:
the fixture drops all tables before each test. Without it, database tests skip.
`tests/conftest.py` provides signed-in actor and product helpers.

Frontend checks: `npm ci`, then `npm run build`; `npm run dev` starts development.
Local Node must be 20.19+ or 22.12+. Use `npm.cmd` on PowerShell when needed.
Bot checks run `npm ci` and `npm test` from `telegram-bot/`. Set `TEST_REDIS_URL`
alongside `TEST_DATABASE_URL` to run the Telegram integration tests.
CI runs Ruff, PostgreSQL and Redis tests, frontend build, bot checks, and Docker image builds.

Before changing a resource, read its corresponding layers and tests. Keep changes
focused, preserve unrelated contracts, and update README for user-facing behavior.
Update this file when an approved change alters architecture or workflow. Report
what changed, which checks passed, and what could not be verified.
