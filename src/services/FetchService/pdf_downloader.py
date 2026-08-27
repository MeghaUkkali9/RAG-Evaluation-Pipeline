import httpx

from src.services.FetchService.retry import retry_on_transient_error


class HttpPdfDownloader:
    """Downloads a PDF's raw bytes over HTTP. Implements PdfDownloader."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    @retry_on_transient_error
    async def download(self, pdf_url: str) -> bytes:
        async with self._http_client.stream("GET", pdf_url) as response:
            response.raise_for_status()
            return b"".join([chunk async for chunk in response.aiter_bytes()])
