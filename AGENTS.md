# Repository guidance

## Purpose and scope

This repository is the foundation for a marketplace similar to Wildberries.
It provides a single FastAPI application in `backend/` with role-based
marketplace APIs (customers, sellers, administrators), admin-only table CRUD,
PostgreSQL persistence, a Redis health check, and a minimal React + Vite
frontend in `front/`.

Follow the architecture and behavior described below when making requested
changes. Keep proposed improvements separate from this file and ask the project
owner before adding them to the documented architecture or implementing them.

## Project map

```text
backend/
  app/
    main.py        # App composition, lifespan, exception handlers, root/health
    api/           # Resource routers and HTTP contracts
    service/       # Application operations and write transaction boundaries
    repository/    # SQLAlchemy queries, persistence, transaction contexts
    models/        # SQLAlchemy table definitions and model registration
    schemas/       # Pydantic create, update, and read schemas
    core/
      config.py    # Environment-based database, Redis, JWT, and admin settings
      db.py        # Declarative Base, async engine factory, session dependency
      security.py  # Password hashing (scrypt) and JWT encode/decode
    exceptions/    # Plain application exceptions
    utils/         # Small shared helpers (email normalization)
  requirements.txt     # Backend runtime dependencies
  requirements-dev.txt # Backend development dependencies
  Dockerfile           # Python 3.12 API image
  .dockerignore        # Backend build context exclusions
front/
  src/
    main.jsx       # React root and global stylesheet import
    App.jsx        # Minimal startup screen
    index.css      # Global styles
  index.html       # HTML entry point
  vite.config.js   # Vite dev server, file watching, API proxy
  package.json     # Frontend dependencies and npm scripts
  package-lock.json # Locked dependency tree used by npm ci
  Dockerfile       # Node.js 24 image running Vite
  .dockerignore    # Excludes local dependencies and build output
compose.yaml           # Frontend, API, PostgreSQL, Redis, and source reload
.env.example           # Example Compose variables
README.md              # Human-facing setup and API documentation
```

`backend/` and `front/` are independent build contexts. Keep shared Compose
configuration, environment examples, Git ignores, and documentation at the root.
The backend Python package is still named `app`; preserve `from app...` imports
and the `app.main:app` entry point. Run backend Python commands from `backend/`.

The package names `service` and `repository` are singular. Resource modules
are singular except for the existing `backend/app/api/users.py`; follow the
surrounding code rather than renaming files as part of unrelated work.

## Layer responsibilities

Request dependency flow:

```text
router -> service -> repository -> AsyncSession -> database
```

- **API:** Declare paths, request/response schemas, status codes, and query
  validation. Inject a service using `Annotated[..., Depends(...)]`. Keep SQL
  and application operations out of route handlers.
- **Service:** Coordinate an operation, detect missing records, choose write
  transaction boundaries, and return Pydantic read schemas. Raise the existing
  plain application exceptions rather than HTTP exceptions.
- **Repository:** Query and mutate ORM records using the injected async session.
  Return ORM records to services. Keep HTTP concerns out of this layer.
- **Models:** Define tables, column types, primary keys, and foreign keys using
  SQLAlchemy `Mapped` and `mapped_column`. Import each model in
  `backend/app/models/__init__.py` so it belongs to the startup metadata.
- **Schemas:** Define input validation and output shape. Read schemas use
  `ConfigDict(from_attributes=True)`; services convert ORM records with
  `model_validate`. Writes use validated data through `model_dump`, except the
  example user repository, which accepts the name directly.
- **Composition:** Register routers and exception handlers in `backend/app/main.py`.
  Dependency factories live alongside their service or repository.

Use the existing resource-specific classes. There are no generic base services,
base repositories, separate domain layer, or microservices in this project.

Marketplace features use feature services that take several repositories:
`auth`, `catalog`, `customer_profile`, `cart`, `customer_order`,
`seller_store`, `seller_order`, and `admin`. Their routers are `api/auth.py`
(`/auth`), `api/catalog.py` (`/catalog`), `api/customer_cabinet.py`
(`/customer`), `api/seller_cabinet.py` (`/seller`), and `api/admin.py`
(`/admin`). Repositories created in one request share its session, so one
repository's `transaction()` covers writes made through the others.
`repository/analytics.py` holds read-only aggregate queries and has no model.

## Frontend

- `front/` is an independent JavaScript React application built with Vite.
  Keep browser code here and backend operations in `backend/app/`.
- `src/main.jsx` mounts `App` inside React StrictMode and imports global styles.
  There are no marketplace pages, client-side routes, or state libraries yet.
- Use npm and preserve `package-lock.json`. The scripts are `dev`, `build`,
  and `preview`; build output goes to `front/dist/` and is ignored by Git.
- Vite listens on `0.0.0.0:5173` with a strict port. Its development proxy maps
  `/api/*` to the backend, removing `/api`. Use relative `/api/...` URLs for
  browser requests rather than Docker service names.
- `API_PROXY_TARGET` configures the server-side proxy: Compose sets
  `http://api:8000`; outside Docker it defaults to `http://localhost:8000`.
  `USE_POLLING=true` enables file polling in Docker for mounted sources.
- The proxy runs in Vite's development and local preview servers. Built static
  assets do not include the proxy; production hosting needs its own API routing.

## Sessions, transactions, and errors

- Application lifespan creates the async database engine and Redis client,
  stores them on `app.state`, and closes them on shutdown.
- `get_db` provides one request-scoped `AsyncSession` with
  `expire_on_commit=False`, closing it after use.
- A service write wraps the entire operation, including any record lookup,
  in `async with self.repository.transaction():`.
- That context uses `AsyncSession.begin()`: successful exit commits and an
  exception rolls back. Repository create/update/delete methods flush changes;
  they do not commit independently. Create/update also refresh the record.
- Marketplace repository transaction contexts translate `IntegrityError` into
  `RecordConflict`. The example user repository exposes `db.begin()` directly.
- `backend/app/main.py` maps `RecordNotFound` and `UserNotFound` to HTTP 404,
  `RecordConflict` to HTTP 409, `AuthenticationFailed` to HTTP 401 (with
  `WWW-Authenticate: Bearer`), `PermissionDenied` to HTTP 403, and
  `BusinessRuleViolation` to HTTP 400, using a JSON `detail` field. Request
  validation uses FastAPI's HTTP 422 responses.
- `AsyncSession.begin()` fails if the session already has a transaction, and
  any read starts one. A write method must therefore enter `transaction()`
  before its first query. For the same reason, the authentication dependencies
  in `service/auth.py` verify the JWT without querying the database.
- Rows that concurrent requests may change (stock, order status) are locked
  with `SELECT ... FOR UPDATE` inside the transaction; checkout locks products
  in primary-key order.

Preserve rollback behavior, including when an exception occurs after a flush.

## Resources and existing API behavior

Table CRUD routes are registered in `main.py` with an admin-only dependency;
the example users stay public.

| Resource | Route prefix | Primary key |
| --- | --- | --- |
| Example users | `/users` | `id` |
| Customers | `/customers` | `customer_id` |
| Sellers | `/sellers` | `seller_id` |
| Products | `/products` | `product_id` |
| Orders | `/orders` | `order_id` |
| Order items | `/order-items` | `order_item_id` |

Each resource has POST and list GET on its prefix, and GET, PUT, DELETE on
`/{primary_key}`. POST returns 201; DELETE returns 204 with an empty body.
PUT requires all writable fields and performs a full replacement. Lists return
JSON arrays ordered by primary key, with `offset=0`, `limit=20`, nonnegative
offsets, and limits from 1 to 100.

Relationships are database foreign keys:

```text
sellers   <- products
customers <- orders
orders    <- order_items -> products
customers <- accounts -> sellers      (nullable, unique, ON DELETE CASCADE)
customers <- cart_items -> products   (ON DELETE CASCADE)
```

Invalid references and deletion of referenced parents return 409. Dependent
records must be deleted first, except accounts and cart items, which cascade.
The example user is independent of customers and sellers; it does not represent
an authentication account. `accounts` holds the login email (unique,
lowercase), password hash, role (`customer`, `seller`, `admin`), and the linked
profile. `products.is_active` marks withdrawn products and
`orders.delivery_address` stores the checkout address (nullable for CRUD
orders).

Use the existing `Decimal`/`Numeric` types for monetary fields and the seller
rating. Preserve schema constraints and the allowed order/payment status values.

`order_date` uses `DateTime(timezone=True)` in the model and `AwareDatetime`
in the schemas. Create and update requests must include `Z` or an explicit UTC
offset; timezone-less dates return 422. PostgreSQL preserves the instant rather
than the original offset.

Through the table CRUD routes, orders and order items stay independent:
callers supply prices, totals, stock, dates, and statuses, and nothing is
recalculated. The marketplace routes apply the business rules documented in
`README.md`: checkout turns the whole cart into one order (snapshotting prices,
reserving stock, emptying the cart); sellers move orders containing their
products `new` → `shipped`/`delivered` and `shipped` → `delivered`; customers
cancel only `new` orders, which returns stock and refunds paid orders;
administrators change payment `pending` → `paid` → `refunded`; deleting a
seller's product withdraws it. The cart lives in PostgreSQL. Redis currently
supports the health check only.

## Runtime and configuration

- Runtime dependencies are FastAPI, Uvicorn, async SQLAlchemy, asyncpg,
  redis-py, and PyJWT.
- `backend/app/core/config.py` reads `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`,
  `ACCESS_TOKEN_EXPIRE_MINUTES`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` from the
  process environment. When both admin variables are set, startup creates that
  administrator account if no account uses the email. The application does not load `.env` itself. Compose reads its
  variables and supplies the connection URLs to the API container.
- `create_engine` converts `postgresql://` URLs to `postgresql+asyncpg://`.
- Startup imports `app.models` and runs `Base.metadata.create_all`. This creates
  missing tables directly from the model definitions, including `order_date` as
  `TIMESTAMP WITH TIME ZONE`. Existing table definitions are not changed by
  startup. No separate schema upgrade scripts are used at this stage; when a
  column is added to an existing table, document the `ALTER TABLE` in
  `README.md` (see "Upgrading an existing database").
- `/health` checks both the database (`SELECT 1`) and Redis (`PING`), returning
  503 if either check fails.
- Compose runs PostgreSQL 17 and Redis 7 with persistent volumes and publishes
  the API on port 8000 and frontend on port 5173 by default. `API_PORT` and
  `FRONT_PORT` control the published ports. It mounts `backend/app/` at `/app/app`
  for API reload and `front/src/`, `front/index.html`, and `front/vite.config.js`
  for frontend reload.
- The frontend image uses Node.js 24 and installs locked dependencies with
  `npm ci`. Dependencies remain in the image; rebuild after package or lockfile
  changes. API builds use `backend/Dockerfile` with `backend/` as their context;
  frontend builds use `front/Dockerfile` with `front/` as their context.

Keep credentials in environment configuration. Do not commit `.env`, virtual
environments, caches, or generated files.

## Development

Run Compose commands from the repository root and backend Python commands from
`backend/`. Backend dependency files and the API Dockerfile live in `backend/`.
The Docker runtimes use Python 3.12 and Node.js 24.

Run Compose stack:

```sh
docker compose up
```

For the standard stack, copy `.env.example` to `.env` if needed, as described
in `README.md`. The frontend is at `http://localhost:5173`; the API and Swagger
UI are at `http://localhost:8000` and `/docs`. Add `--build` after dependency or
Dockerfile changes, and `-d` for background operation.

Backend tests run from `backend/` with `python -m pytest`. API tests need
`TEST_DATABASE_URL` pointing to a disposable PostgreSQL database (wiped before
each test); without it they are skipped. `tests/conftest.py` provides helpers
for registering customers and sellers and signing in as the administrator.

For frontend-only development, run `npm ci` then `npm run dev` from `front/`
with Node.js 20.19+ or 22.12+. Use `npm.cmd` on PowerShell if needed. The local
API must be running separately for proxied requests. `npm run build` produces
the static frontend, and `npm run preview` serves it locally.

## Making changes

- Read the corresponding model, schema, repository, service, and router
  before changing a resource. Use a marketplace resource such as `customer`
  as the reference for its existing CRUD pattern.
- Keep changes focused on the request. Preserve public paths, field names,
  status codes, and replacement semantics unless changing them is in scope.
- For an authorized new resource, add its model, schemas, repository, service,
  and router; register the model and router.
- Keep database operations asynchronous. Match the existing Python naming,
  annotations, and explicit imports.
- Update `README.md` when an implemented change affects setup or API behavior.
  Update this file when an approved change alters the architecture or workflow.
- Report changed behavior, checks performed, and any checks that could not run.
