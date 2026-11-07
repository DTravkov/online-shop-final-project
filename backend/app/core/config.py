import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# JWT access tokens. Override JWT_SECRET outside local development.
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# When both are set, startup creates this administrator account if it is missing.
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
