from typing import Protocol

from src.services.FetchService.schemas import PaperMetadata


class MetadataFetcher(Protocol):
    """Looks up paper metadata for a given paper id from some source."""

    async def fetch(self, paper_id: str) -> PaperMetadata: ...


class PdfDownloader(Protocol):
    """Downloads a PDF's raw bytes from a URL."""

    async def download(self, pdf_url: str) -> bytes: ...
