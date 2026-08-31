from typing import Protocol

from opensearchpy import AsyncOpenSearch

from src.services.RetrievalService.schemas import SearchHit


class Retriever(Protocol):
    async def search(self, query: str, top_k: int) -> list[SearchHit]: ...


class Bm25Retriever:
    """Plain BM25 search over an OpenSearch index. One of several Retriever
    implementations - VectorRetriever and HybridRetriever plug in later
    behind the same interface once an embedding model is chosen."""

    def __init__(self, opensearch_client: AsyncOpenSearch, index_name: str):
        self._opensearch_client = opensearch_client
        self._index_name = index_name

    async def search(self, query: str, top_k: int) -> list[SearchHit]:
        response = await self._opensearch_client.search(
            index=self._index_name,
            body={
                "size": top_k,
                "query": {"match": {"content": query}},
            },
        )

        return [
            SearchHit(
                arxiv_id=hit["_source"]["arxiv_id"],
                chunk_index=hit["_source"]["chunk_index"],
                section_title=hit["_source"]["section_title"],
                content=hit["_source"]["content"],
                score=hit["_score"],
            )
            for hit in response["hits"]["hits"]
        ]
