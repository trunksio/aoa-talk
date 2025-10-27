"""
Configuration management using pydantic-settings
"""

from functools import lru_cache
from typing import List
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql://cavia:caviadev123@localhost:5432/cavia",
        description="PostgreSQL connection URL",
    )

    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="minioadmin")
    minio_secret_key: str = Field(default="minioadmin123")
    minio_secure: bool = Field(default=False)

    # Ollama
    ollama_host: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3:8b")

    # Agent Configuration
    agent_timeout: int = Field(default=60, description="Agent timeout in seconds")
    agent_max_retries: int = Field(default=3)
    agent_heartbeat_interval: int = Field(
        default=30, description="Heartbeat interval in seconds"
    )

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=4)

    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production")
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", description="json or text")

    # Queue Names
    queue_orchestration: str = Field(default="orchestrator")
    queue_parsing: str = Field(default="cv-parsing")
    queue_evaluation: str = Field(default="cv-evaluation")
    queue_reporting: str = Field(default="cv-reporting")

    # Embedding Model
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
