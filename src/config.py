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

@lru_cache
def get_settings() -> Settings:
    return Settings()
