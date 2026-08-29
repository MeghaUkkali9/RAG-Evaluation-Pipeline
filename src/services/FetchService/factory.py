from pathlib import Path

import httpx

from src.config import Settings
from src.services.FetchService.arxiv_metadata_fetcher import ArxivMetadataFetcher
from src.services.FetchService.client import FetchServiceClient
from src.services.FetchService.pdf_downloader import HttpPdfDownloader
from src.services.FetchService.retry import RateLimiter


def create_fetch_service_client(settings: Settings) -> FetchServiceClient:
    timeout = httpx.Timeout(
        settings.fetch_http_timeout_seconds,
        connect=settings.fetch_http_connect_timeout_seconds,
    )
    http_client = httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    )
    rate_limiter = RateLimiter(
        min_interval_seconds=settings.arxiv_rate_limit_seconds,
    )
    metadata_fetcher = ArxivMetadataFetcher(
        http_client=http_client,
        api_base=settings.arxiv_api_base,
        rate_limiter=rate_limiter,
    )
    pdf_downloader = HttpPdfDownloader(
        http_client=http_client,
        rate_limiter=rate_limiter,
        cache_dir=Path(settings.pdf_cache_dir),
    )

    return FetchServiceClient(
        http_client=http_client,
        metadata_fetcher=metadata_fetcher,
        pdf_downloader=pdf_downloader,
    )
