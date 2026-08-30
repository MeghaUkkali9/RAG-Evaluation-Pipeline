from opensearchpy import AsyncOpenSearch

from src.config import Settings
from src.services.IndexingService.client import IndexingServiceClient


def create_indexing_service_client(settings: Settings) -> IndexingServiceClient:
    opensearch_client = AsyncOpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=False,
    )

    return IndexingServiceClient(
        opensearch_client=opensearch_client,
        index_name=settings.opensearch_index,
    )
