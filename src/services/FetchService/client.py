from typing import Protocol

import httpx

from src.services.FetchService.schemas import FetchedPaper, PaperMetadata


class MetadataFetcher(Protocol):
    async def fetch(self, paper_id: str) -> PaperMetadata: ...


class PdfDownloader(Protocol):
    async def download(self, pdf_url: str) -> bytes: ...


class FetchServiceClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        metadata_fetcher: MetadataFetcher,
        pdf_downloader: PdfDownloader,
    ):
        self._http_client = http_client
        self._metadata_fetcher = metadata_fetcher
        self._pdf_downloader = pdf_downloader

    async def __aenter__(self) -> "FetchServiceClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def fetch_paper_metadata(self, paper_id: str) -> PaperMetadata:
        return await self._metadata_fetcher.fetch(paper_id)

    async def fetch_paper(self, paper_id: str) -> FetchedPaper:
        metadata = await self._metadata_fetcher.fetch(paper_id)
        pdf_bytes = await self._pdf_downloader.download(metadata.pdf_url)

        return FetchedPaper(metadata=metadata, pdf_bytes=pdf_bytes)
