import logging

from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk

from src.exceptions.indexing_service import IndexingServiceError
from src.services.ChunkingService.schemas import Chunk

logger = logging.getLogger(__name__)


def build_chunks_index_mapping(vector_dimensions: int | None = None) -> dict:
    """`content` uses OpenSearch's normal text mapping, which is scored
    with BM25 already, no setup needed. The `embedding` knn_vector field
    only gets added if a dimension is given - so a BM25-only index (like
    the live app has right now) stays the same unless it asks for it."""
    properties = {
        "arxiv_id": {"type": "keyword"},
        "chunk_index": {"type": "integer"},
        "section_title": {"type": "keyword"},
        "content": {"type": "text"},
    }

    if vector_dimensions is None:
        return {"mappings": {"properties": properties}}

    properties["embedding"] = {
        "type": "knn_vector",
        "dimension": vector_dimensions,
        "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "lucene"},
    }
    return {
        "settings": {"index": {"knn": True}},
        "mappings": {"properties": properties},
    }


class IndexingServiceClient:
    def __init__(self, opensearch_client: AsyncOpenSearch, index_name: str):
        self._opensearch_client = opensearch_client
        self._index_name = index_name

    async def ensure_index(self, vector_dimensions: int | None = None) -> None:
        
        if not await self._opensearch_client.indices.exists(index=self._index_name):
            
            await self._opensearch_client.indices.create(
                index=self._index_name, 
                body=build_chunks_index_mapping(vector_dimensions)
            )

    async def index_paper_chunks(
        self,
        arxiv_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        actions = []
        for i, chunk in enumerate(chunks):
            source = {
                "arxiv_id": arxiv_id,
                "chunk_index": chunk.chunk_index,
                "section_title": chunk.section_title,
                "content": chunk.content,
            }
            if embeddings is not None:
                source["embedding"] = embeddings[i]

            actions.append(
                {
                    "_index": self._index_name,
                    "_id": f"{arxiv_id}-{chunk.chunk_index}",
                    "_source": source,
                }
            )

        try:
            await async_bulk(self._opensearch_client, actions)
        except Exception as e:
            logger.exception("Failed to index chunks in OpenSearch for '%s'", arxiv_id)
            raise IndexingServiceError(f"Failed to index chunks for '{arxiv_id}': {e}") from e

    async def aclose(self) -> None:
        await self._opensearch_client.close()
