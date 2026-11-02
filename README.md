# Online Shop API

Minimal FastAPI, PostgreSQL, and Redis project using Docker Compose.

## Run

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

## API tests

Install development dependencies and run the tests from the project root:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
```

Add future tests in `tests/test_<feature>.py`, following `tests/test_main.py`.
Tests use FastAPI's test client without running application startup, so the
example tests do not require Docker or database connections.
