from typing import Protocol
from opensearchpy import AsyncOpenSearch

from src.services.EmbeddingService.client import EmbeddingClient
from src.services.RetrievalService.schemas import SearchHit


class Retriever(Protocol):
    async def search(self, query: str, top_k: int) -> list[SearchHit]: ...


def _hits_from_response(response: dict) -> list[SearchHit]:
    hits = []
    for hit in response["hits"]["hits"]:
        hits.append(
            SearchHit(
                arxiv_id=hit["_source"]["arxiv_id"],
                chunk_index=hit["_source"]["chunk_index"],
                section_title=hit["_source"]["section_title"],
                content=hit["_source"]["content"],
                score=hit["_score"],
            )
        )
    return hits


class Bm25Retriever:
    """Plain BM25 (keyword) search over OpenSearch index."""

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

        return _hits_from_response(response)


class VectorRetriever:
    """Searches by meaning instead of keywords.
    Turns the query text into a vector with the same model I used for the
    corpus then asks OpenSearch for the closest vectors to it."""

    def __init__(
        self, 
        opensearch_client: AsyncOpenSearch,
        index_name: str, 
        embedding_client: EmbeddingClient
    ):
        self._opensearch_client = opensearch_client
        self._index_name = index_name
        self._embedding_client = embedding_client
        # this can read the total tokens spent on query embedding for cost tracking.
        self.tokens_used = 0

    async def search(self, query: str, top_k: int) -> list[SearchHit]:
        embeddings, tokens = await self._embedding_client.embed([query])
        
        self.tokens_used += tokens
        query_vector = embeddings[0]

        response = await self._opensearch_client.search(
            index=self._index_name,
            body={
                "size": top_k,
                "query": {"knn": {"embedding": {"vector": query_vector, "k": top_k}}},
            },
        )

        return _hits_from_response(response)
