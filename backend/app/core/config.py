"""
FinRAG Backend — Core Configuration
Loads settings from environment variables and .env file.
"""

from functools import lru_cache
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "FinRAG"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # CORS
    frontend_url: str = "http://localhost:3000"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "finrag"
    postgres_user: str = "finrag_user"
    postgres_password: str = "finrag_password"
    database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # File uploads
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 100

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # FAISS
    faiss_index_path: str = "./faiss_index"
    faiss_top_k: int = 10

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    # LLM
    llm_provider: Literal["openai", "anthropic", "google", "huggingface", "none"] = "none"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"

    # Google
    google_api_key: Optional[str] = None
    google_model: str = "gemini-1.5-flash"

    # HuggingFace
    hf_model_name: str = "microsoft/phi-2"
    hf_device: str = "cpu"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
