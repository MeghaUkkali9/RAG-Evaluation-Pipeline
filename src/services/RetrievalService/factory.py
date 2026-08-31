from opensearchpy import AsyncOpenSearch

from src.services.RetrievalService.client import Bm25Retriever


def create_bm25_retriever(opensearch_client: AsyncOpenSearch, index_name: str) -> Bm25Retriever:
    return Bm25Retriever(opensearch_client=opensearch_client, index_name=index_name)
