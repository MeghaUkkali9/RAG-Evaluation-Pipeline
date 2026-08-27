from src.exceptions import ArxivEntryNotFoundError, FetchServiceError
from src.services.FetchService.arxiv_metadata_fetcher import ArxivMetadataFetcher
from src.services.FetchService.client import FetchServiceClient
from src.services.FetchService.factory import create_fetch_service_client
from src.services.FetchService.interfaces import MetadataFetcher, PdfDownloader
from src.services.FetchService.pdf_downloader import HttpPdfDownloader
from src.services.FetchService.schemas import FetchedPaper, PaperMetadata

__all__ = [
    "FetchServiceError",
    "ArxivEntryNotFoundError",
    "ArxivMetadataFetcher",
    "FetchServiceClient",
    "create_fetch_service_client",
    "MetadataFetcher",
    "PdfDownloader",
    "HttpPdfDownloader",
    "FetchedPaper",
    "PaperMetadata",
]
