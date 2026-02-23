from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/link_shortener"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MIN: int = 30

    # Application
    BASE_URL: str = "http://localhost:8000"
    SHORT_LINK_PREFIX: str = "opupupa"
    DEFAULT_CACHE_TTL_SEC: int = 86400  # 24 hours
    PURGE_INTERVAL_SEC: int = 300  # 5 minutes

    # Development
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # CORS (optional)
    CORS_ORIGINS: str = ""

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()
