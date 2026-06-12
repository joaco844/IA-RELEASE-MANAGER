"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "AI Release Manager"
    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/release_manager"

    # Auth / crypto
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    # Fernet key used to encrypt third-party tokens at rest. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # Rate limiting
    rate_limit_default: str = "120/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_generate: str = "20/hour"

    # AI provider
    ai_provider: Literal["openai", "gemini"] = "openai"
    ai_temperature: float = 0.2
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    gemini_embedding_model: str = "models/text-embedding-004"

    # RAG
    rag_enabled: bool = True
    rag_persist_dir: str = "./data/chroma"
    rag_top_k: int = 6

    # Workflow
    qa_max_revisions: int = 2
    node_max_retries: int = 3
    hours_saved_per_release: float = 3.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
