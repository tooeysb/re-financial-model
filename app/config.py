"""
Application configuration using Pydantic Settings.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


def get_env_file() -> str:
    """Determine which env file to use based on environment."""
    env = os.getenv("APP_ENV", "development")
    if env == "production":
        return ".env.production"
    return ".env.development"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./dev.db"

    # App settings
    app_name: str = "RE Financial Model"
    debug: bool = False
    log_level: str = "INFO"
    app_env: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # JWT Configuration
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION-USE-LONG-RANDOM-STRING"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Token Expiration
    password_reset_token_expire_hours: int = 24
    invite_token_expire_days: int = 7

    # SendGrid Email
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@example.com"
    sendgrid_from_name: str = "RE Financial Model"

    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:8000"

    # Initial Admin (for first-time setup)
    initial_admin_email: str = ""
    initial_admin_password: str = ""

    class Config:
        env_file = get_env_file()
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
