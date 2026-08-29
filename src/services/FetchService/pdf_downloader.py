import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from src.services.FetchService.retry import RateLimiter, retry_request


class HttpPdfDownloader:
    def __init__(self, http_client: httpx.AsyncClient, rate_limiter: RateLimiter, cache_dir: Path):
        self._http_client = http_client
        self._rate_limiter = rate_limiter
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, pdf_url: str) -> bytes:
        cache_path = self._cache_path(pdf_url)

        if cache_path.exists():
            return cache_path.read_bytes()

        async def send_request() -> bytes:
            await self._rate_limiter.wait()

            async with self._http_client.stream("GET", pdf_url) as response:
                response.raise_for_status()
                return b"".join([chunk async for chunk in response.aiter_bytes()])

        pdf_bytes = await retry_request(send_request)
        cache_path.write_bytes(pdf_bytes)
        return pdf_bytes

    def _cache_path(self, pdf_url: str) -> Path:
        return self._cache_dir / f"{self._cache_key(pdf_url)}.pdf"

    def _cache_key(self, pdf_url: str) -> str:
        path_segment = urlparse(pdf_url).path.rstrip("/").rsplit("/", 1)[-1]

        if path_segment:
            return path_segment

        return hashlib.sha256(pdf_url.encode()).hexdigest()
