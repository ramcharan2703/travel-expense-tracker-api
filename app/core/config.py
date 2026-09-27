from functools import lru_cache
from typing import Literal
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application settings
    PROJECT_NAME: str = "Travel Expense Tracker API"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS settings
    CORS_ORIGINS: str = ""

    # Logging settings
    LOG_LEVEL: str = "INFO"

    # Database settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "travel_expense_tracker"


@lru_cache
def get_settings() -> Settings:
    """Returns a cached singleton instance of application settings."""
    return Settings()


settings = get_settings()
