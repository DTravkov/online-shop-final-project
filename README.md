# Online Shop API

Minimal FastAPI, PostgreSQL, and Redis project using Docker Compose.

## Application structure

```text
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
```

Dependencies flow `router -> service -> repository -> database` using
FastAPI `Depends`. Each request gets an async SQLAlchemy session, closed after
the request. Services define write transaction boundaries using the repository's
transaction context: success commits and exceptions roll back. Repository writes
only flush changes, so multiple writes can share one service transaction. Services return
Pydantic schemas and raise plain exceptions; the application maps missing records
to HTTP 404 and database integrity conflicts to HTTP 409. There are no generic
base repositories or service abstractions.

The example user has an integer `id` and a `name` (1–100 characters):

- `POST /users` — create with `{"name": "Alice"}`
- `GET /users?offset=0&limit=20` — list (maximum 100 per request)
- `GET /users/{user_id}` — read
- `PUT /users/{user_id}` — replace the name
- `DELETE /users/{user_id}` — delete, returning HTTP 204

Tables are created on startup for this basic example. Schema changes to existing
tables will need migrations later. The user example does not include authentication.

The document's `customers`, `sellers`, `products`, `orders`, and `order_items`
tables have SQLAlchemy models in `app/models` and create, update, and read schemas
in `app/schemas`. All models are registered by importing `app.models` at startup.
Document fields are required; update schemas describe full replacements.

Each marketplace resource has its own router, service, and repository:

| Resource | Base path | Primary key |
| --- | --- | --- |
| Customers | `/customers` | `customer_id` |
| Sellers | `/sellers` | `seller_id` |
| Products | `/products` | `product_id` |
| Orders | `/orders` | `order_id` |
| Order items | `/order-items` | `order_item_id` |

All support `POST` and paginated `GET` on the base path, plus `GET`, `PUT`, and
`DELETE` on `/{primary_key}`. Creates return 201; deletes return 204. Lists use
`offset=0&limit=20` by default, with a maximum limit of 100.

Foreign keys must reference existing records. Deleting a referenced parent
returns 409; delete dependent records first. Failed writes roll back. Orders and
order items are independent CRUD records: stock, order totals, and payment state
are supplied by the caller, with no checkout or automatic recalculation logic.

## Tests

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
```

CRUD tests use an isolated in-memory SQLite database and the actual DI chain;
marketplace tests enforce foreign keys and check persistence, validation,
restricted deletes, and rollback. PostgreSQL and Redis are not needed for these tests.

## Run

### Development with automatic reload

Use the self-contained development Compose file:

```sh
docker compose -f compose.dev.yaml up --build
```

The app source is mounted into the API container. Saving a Python file under
`app/` restarts Uvicorn automatically; changes are checked every 0.25 seconds.
PostgreSQL and Redis are included in this file. Dependency or Dockerfile
changes require rerunning the command with `--build`.

Stop the development services with:

```sh
docker compose -f compose.dev.yaml down
```

### Standard run

Install Docker with the Compose plugin, then copy the example environment file:

```sh
cp .env.example .env
```

On PowerShell:

```powershell
Copy-Item .env.example .env
```

Start the services:

```sh
docker compose up --build -d
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The health endpoint checks both PostgreSQL and Redis and returns HTTP 503 if either is unavailable. PostgreSQL and Redis data persist in Docker volumes. Only the API port is published to the host.

The example credentials are for local development. Use a URL-safe password in `.env` because it is included in the database connection URL.

Stop the services:

```sh
docker compose down
```
