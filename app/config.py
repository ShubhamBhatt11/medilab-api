"""App settings.

pydantic-settings reads env vars (and .env) into a typed object — the
FastAPI-world equivalent of a validated process.env + dotenv in Express,
except missing/invalid values fail at startup instead of at first use.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/medilab"
    jwt_secret: str = "dev-only-secret-do-not-use-in-prod-override-via-env"
    jwt_expires_minutes: int = 60 * 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
