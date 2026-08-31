from src.repositories.PaperRepository import PaperRepository
from src.services.ChunkingService.client import ChunkingServiceClient
from src.services.FetchService.client import FetchServiceClient
from src.services.FetchService.schemas import PaperMetadata
from src.services.IndexingService.client import IndexingServiceClient


class IngestionService:
    def __init__(
        self,
        fetch_service_client: FetchServiceClient,
        chunking_service_client: ChunkingServiceClient,
        indexing_service_client: IndexingServiceClient,
        paper_repository: PaperRepository,
    ):
        self._fetch_service_client = fetch_service_client
        self._chunking_service_client = chunking_service_client
        self._indexing_service_client = indexing_service_client
        self._paper_repository = paper_repository

    async def ingest_paper(self, arxiv_id: str) -> PaperMetadata:
        fetched = await self._fetch_service_client.fetch_paper(arxiv_id)

        parsed = await self._chunking_service_client.parse(fetched.pdf_bytes)
        self._paper_repository.save_paper(fetched.metadata, parsed)

        chunks = self._chunking_service_client.chunk(
            fetched.metadata.title, fetched.metadata.abstract, parsed
        )
        await self._indexing_service_client.index_paper_chunks(fetched.metadata.arxiv_id, chunks)

        return fetched.metadata
