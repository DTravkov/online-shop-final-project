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
to HTTP 404 and database integrity conflicts to HTTP 409. There are no generic
base repositories or service abstractions.

The example user has an integer `id` and a `name` (1–100 characters):

- `POST /users` — create with `{"name": "Alice"}`
- `GET /users?offset=0&limit=20` — list (maximum 100 per request)
- `GET /users/{user_id}` — read
- `PUT /users/{user_id}` — replace the name
- `DELETE /users/{user_id}` — delete, returning HTTP 204

SQLAlchemy models define the initial database schema. Missing tables are created
on startup, including the timezone-aware order date column. Existing table
definitions are not changed by startup. The user example does not include
authentication.

The document's `customers`, `sellers`, `products`, `orders`, and `order_items`
tables have SQLAlchemy models in `backend/app/models` and create, update, and read
schemas in `backend/app/schemas`. All models are registered by importing
`app.models` at startup.
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

Order dates must include a timezone: for example,
`"order_date": "2026-11-05T10:31:56.731Z"` or
`"order_date": "2026-11-05T15:31:56.731+05:00"`. PostgreSQL stores the instant
using `TIMESTAMP WITH TIME ZONE`; the original offset is not retained. Dates
without a timezone return HTTP 422.

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
after changing dependencies or a Dockerfile, and add `-d` to run in the background.
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
