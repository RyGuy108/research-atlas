from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Research Atlas API"
    app_version: str = "0.1.0"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    openalex_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-mini"
    openai_max_retries: int = Field(default=2, ge=0, le=5)
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    extraction_max_output_tokens: int = Field(default=2_500, ge=256, le=10_000)
    extraction_concurrency: int = Field(default=3, ge=1, le=10)
    arxiv_base_url: str = "https://export.arxiv.org"
    openalex_base_url: str = "https://api.openalex.org"
    provider_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ranking_result_limit: int = Field(default=25, ge=1, le=100)
    cross_encoder_candidate_limit: int = Field(default=50, ge=1, le=200)
    cross_encoder_enabled: bool = False
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    cross_encoder_device: str | None = None
    cross_encoder_batch_size: int = Field(default=16, ge=1, le=128)
    database_url: str = (
        "postgresql+asyncpg://research_atlas:research_atlas@localhost:5432/research_atlas"
    )


@lru_cache
def get_settings() -> Settings:
    # Settings are immutable during a process, so loading the environment once is sufficient.
    return Settings()
