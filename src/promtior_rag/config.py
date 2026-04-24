"""Application settings loaded from environment variables."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(str, Enum):
    CONSOLE = "console"
    JSON = "json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.DEVELOPMENT
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.CONSOLE

    openai_api_key: SecretStr
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024, gt=0, le=16384)

    cohere_api_key: SecretStr
    rerank_model: str = "rerank-english-v3.0"
    rerank_top_n: int = Field(default=4, gt=0, le=20)

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "promtior-rag"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    promtior_web_url: str = "https://www.promtior.ai/sitemap.xml"
    promtior_web_max_depth: int = Field(default=3, ge=1, le=5)
    promtior_pdf_path: Path = Path("./data/AI_Engineer.pdf")

    chunk_size: int = Field(default=1000, ge=100, le=8000)
    chunk_overlap: int = Field(default=200, ge=0)
    vector_store_path: Path = Path("./data/vector_store")

    retriever_top_k: int = Field(default=10, ge=1, le=50)
    retriever_semantic_weight: float = Field(default=0.6, ge=0.0, le=1.0)

    server_host: str = "0.0.0.0"  # noqa: S104
    server_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = "*"

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]