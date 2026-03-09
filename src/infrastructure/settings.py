from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/link_shortener"

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MIN: int = 30

    BASE_URL: str = "http://localhost:8000"
    SHORT_LINK_PREFIX: str = "opupupa" #чисто захотелось
    #ну тут от балды если честно, как и в рейт лимитах
    #как бы учебный проект, а эти штуки лучше подгонять по железу
    DEFAULT_CACHE_TTL_SEC: int = 86400  #24 часа
    PURGE_INTERVAL_SEC: int = 300  #5 минут
    UNUSED_LINK_TTL_DAYS: int = 90

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    CORS_ORIGINS: str = ""

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()