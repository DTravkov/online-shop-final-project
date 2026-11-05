# Repository guidance

## Purpose and scope

This repository is the backend foundation for a marketplace similar to
Wildberries. It currently provides a single FastAPI application with CRUD APIs,
PostgreSQL persistence, and a Redis health check. There is no frontend here.

Follow the architecture and behavior described below when making requested
changes. Keep proposed improvements separate from this file and ask the project
owner before adding them to the documented architecture or implementing them.

## Project map

```text
app/
  main.py          # App composition, lifespan, exception handlers, root/health
  api/             # Resource routers and HTTP contracts
  service/         # Application operations and write transaction boundaries
  repository/      # SQLAlchemy queries, persistence, transaction contexts
  models/          # SQLAlchemy table definitions and model registration
  schemas/         # Pydantic create, update, and read schemas
  core/
    config.py      # Environment-based database and Redis URLs
    db.py          # Declarative Base, async engine factory, session dependency
  exceptions/      # Plain application exceptions
  utils/           # Currently empty; reserved for small shared helpers
requirements.txt       # Runtime dependencies
Dockerfile             # Python 3.12 API image
compose.yaml           # API, PostgreSQL, and Redis
compose.dev.yaml       # Standalone development stack with source reload
.env.example           # Example Compose variables
README.md              # Human-facing setup and API documentation
```

The package names `service` and `repository` are singular. Resource modules
are singular except for the existing `app/api/users.py`; follow the surrounding
code rather than renaming files as part of unrelated work.

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
  `app/models/__init__.py` so it belongs to the startup metadata.
- **Schemas:** Define input validation and output shape. Read schemas use
  `ConfigDict(from_attributes=True)`; services convert ORM records with
  `model_validate`. Writes use validated data through `model_dump`, except the
  example user repository, which accepts the name directly.
- **Composition:** Register routers and exception handlers in `app/main.py`.
  Dependency factories live alongside their service or repository.

Use the existing resource-specific classes. There are no generic base services,
base repositories, separate domain layer, or microservices in this project.

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
- `app/main.py` maps `RecordNotFound` and `UserNotFound` to HTTP 404 and
  `RecordConflict` to HTTP 409, using a JSON `detail` field. Request validation
  uses FastAPI's HTTP 422 responses.

Preserve rollback behavior, including when an exception occurs after a flush.

## Resources and existing API behavior

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
```

Invalid references and deletion of referenced parents return 409. Dependent
records must be deleted first. The example user is independent of customers
and sellers; it does not represent an authentication account.

Use the existing `Decimal`/`Numeric` types for monetary fields and the seller
rating. Preserve schema constraints and the allowed order/payment status values.

Orders and order items are independent CRUD resources. Callers supply prices,
totals, stock quantities, dates, and statuses. Item writes do not adjust stock
or recalculate order totals. Authentication, checkout, and payment processing
are not implemented. Redis currently supports the health check only.

## Runtime and configuration

- Runtime dependencies are FastAPI, Uvicorn, async SQLAlchemy, asyncpg, and
  redis-py.
- `app/core/config.py` reads `DATABASE_URL` and `REDIS_URL` from the process
  environment. The application does not load `.env` itself. Compose reads its
  variables and supplies the connection URLs to the API container.
- `create_engine` converts `postgresql://` URLs to `postgresql+asyncpg://`.
- Startup imports `app.models` and runs `Base.metadata.create_all`. This creates
  missing tables; it does not migrate existing table definitions. No migration
  tooling is currently configured.
- `/health` checks both the database (`SELECT 1`) and Redis (`PING`), returning
  503 if either check fails.
- Compose runs PostgreSQL 17 and Redis 7 with persistent volumes and publishes
  the API on port 8000 by default. Development Compose mounts `app/` for reload.

Keep credentials in environment configuration. Do not commit `.env`, virtual
environments, caches, or generated files.

## Development

Run commands from the repository root.
The Docker runtime uses Python 3.12.

Run Compose stack:

```sh
docker compose up --build -d
```

For the standard stack, copy `.env.example` to `.env` if needed, as described
in `README.md`. The API and Swagger UI are at `http://localhost:8000` and `/docs`.

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
