from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    arxiv_api_base: str = "http://export.arxiv.org/api/query"
    arxiv_rate_limit_seconds: float = 3.0
    fetch_http_timeout_seconds: float = 30.0
    fetch_http_connect_timeout_seconds: float = 10.0
    pdf_cache_dir: str = ".cache/pdfs"
    database_url: str = "postgresql+psycopg2://rag_user:rag_user@localhost:5432/rag_pipeline"
    chunking_strategy: str = "section_aware_academic"

    pdf_max_pages: int = 100
    pdf_max_file_size_mb: int = 50

    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "paper_chunks"
    opensearch_use_ssl: bool = False

    embedding_model: str = "text-embedding-3-small"

@lru_cache
def get_settings() -> Settings:
    return Settings()
