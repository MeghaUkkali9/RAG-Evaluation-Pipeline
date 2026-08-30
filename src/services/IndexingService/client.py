import logging

from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk

from src.exceptions.indexing_service import IndexingServiceError
from src.services.ChunkingService.schemas import Chunk

logger = logging.getLogger(__name__)

# `content` uses OpenSearch's default text mapping, which is scored with BM25
# out of the box. A `knn_vector` field can be added here later, once an
# embedding model is chosen, to support hybrid BM25 + vector (HNSW) retrieval.
CHUNKS_INDEX_MAPPINGS = {
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "section_title": {"type": "keyword"},
            "content": {"type": "text"},
        }
    }
}


class IndexingServiceClient:
    def __init__(self, opensearch_client: AsyncOpenSearch, index_name: str):
        self._opensearch_client = opensearch_client
        self._index_name = index_name

    async def ensure_index(self) -> None:
        if not await self._opensearch_client.indices.exists(index=self._index_name):
            await self._opensearch_client.indices.create(
                index=self._index_name, body=CHUNKS_INDEX_MAPPINGS
            )

    async def index_paper_chunks(self, arxiv_id: str, chunks: list[Chunk]) -> None:
        actions = [
            {
                "_index": self._index_name,
                "_id": f"{arxiv_id}-{chunk.chunk_index}",
                "_source": {
                    "arxiv_id": arxiv_id,
                    "chunk_index": chunk.chunk_index,
                    "section_title": chunk.section_title,
                    "content": chunk.content,
                },
            }
            for chunk in chunks
        ]

        try:
            await async_bulk(self._opensearch_client, actions)
        except Exception as e:
            logger.exception("Failed to index chunks in OpenSearch for '%s'", arxiv_id)
            raise IndexingServiceError(f"Failed to index chunks for '{arxiv_id}': {e}") from e

    async def aclose(self) -> None:
        await self._opensearch_client.close()
