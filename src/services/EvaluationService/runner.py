import time

from opensearchpy import AsyncOpenSearch
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.services.ChunkingService.schemas import Chunk, ParsedDocument, Section
from src.services.ChunkingService.strategies import build_chunking_strategy
from src.services.EmbeddingService.client import EMBEDDING_MODEL_SPECS, EmbeddingClient
from src.services.EvaluationService.retrieval_evaluator import evaluate_retrieval
from src.services.EvaluationService.schemas import (
    ExperimentConfig,
    ExperimentResult,
    GoldenQuery,
    OpsMetrics,
)
from src.services.IndexingService.client import IndexingServiceClient
from src.services.RetrievalService.client import Bm25Retriever, Retriever, VectorRetriever
from src.services.RetrievalService.schemas import SearchHit


class ExperimentRunner:
    """Runs one ExperimentConfig from start to end: build a new OpenSearch
    index just for this run (not the real paper_chunks index), chunk (and
    embed, if vector mode) every paper we already ingested, run all golden
    queries on it, and give back the score."""

    def __init__(
        self,
        opensearch_client: AsyncOpenSearch,
        session: Session,
        embedding_client: EmbeddingClient | None = None,
    ):
        self._opensearch_client = opensearch_client
        self._session = session
        self._embedding_client = embedding_client
        self._embedding_tokens = 0
        self._corpus_embedding_latency_ms = 0.0

    async def run(self, config: ExperimentConfig, golden_queries: list[GoldenQuery]) -> ExperimentResult:
        vector_dimensions = self._resolve_vector_dimensions(config)
        self._embedding_tokens = 0
        self._corpus_embedding_latency_ms = 0.0

        index_name = f"experiment_{config.name}"

        await self._reset_index(index_name)
        indexer = IndexingServiceClient(self._opensearch_client, index_name)
        await indexer.ensure_index(vector_dimensions=vector_dimensions)
        await self._index_all_papers(indexer, config)

        # OpenSearch does not make new documents searchable right away - it
        # needs a background refresh (about 1s by default). If we skip this
        # and search too soon, a run that finished indexing fast (fewer,
        # bigger chunks) can query before its own data is visible, and we
        # get a wrong near-zero score even if the chunking is fine.
        await self._opensearch_client.indices.refresh(index=index_name)

        retriever = self._build_retriever(config, index_name)
        hits_by_query, latencies_ms = await self._run_queries(retriever, golden_queries, config.top_k)

        retrieval_metrics, per_query = evaluate_retrieval(golden_queries, hits_by_query, config.top_k)
        ops_metrics = self._build_ops_metrics(
            await self._index_size_bytes(index_name), latencies_ms, config.embedding_model
        )

        return ExperimentResult(config=config, retrieval=retrieval_metrics, ops=ops_metrics, per_query=per_query)

    def _resolve_vector_dimensions(self, config: ExperimentConfig) -> int | None:
        if config.retrieval_mode != "vector":
            return None

        if not config.embedding_model:
            raise ValueError("retrieval_mode='vector' requires an embedding_model")
        if self._embedding_client is None:
            raise ValueError("retrieval_mode='vector' requires an embedding_client")

        return EMBEDDING_MODEL_SPECS[config.embedding_model]["dimensions"]

    def _build_retriever(self, config: ExperimentConfig, index_name: str) -> Retriever:
        if config.retrieval_mode == "vector":
            return VectorRetriever(self._opensearch_client, index_name, self._embedding_client)
        return Bm25Retriever(self._opensearch_client, index_name)

    async def _reset_index(self, index_name: str) -> None:
        # We delete and make it again instead of reusing the old one. That
        # way, running the same experiment name twice always gives a clean
        # result, and we don't end up with old documents left over from a
        # previous run mixed into the new one.
        if await self._opensearch_client.indices.exists(index=index_name):
            await self._opensearch_client.indices.delete(index=index_name)

    async def _index_all_papers(self, indexer: IndexingServiceClient, config: ExperimentConfig) -> None:
        chunker = build_chunking_strategy(config.chunking_strategy)
        papers = self._session.query(Paper).all()

        chunks_by_paper: list[tuple[str, list[Chunk]]] = []
        for paper in papers:
            sections = []
            for section in paper.sections:
                sections.append(Section(**section))

            parsed = ParsedDocument(raw_text=paper.raw_text, sections=sections)
            chunks = chunker.chunk(paper.title, paper.abstract, parsed)
            chunks_by_paper.append((paper.arxiv_id, chunks))

        embeddings_by_paper = await self._embed_corpus(config, chunks_by_paper)

        for arxiv_id, chunks in chunks_by_paper:
            embeddings = embeddings_by_paper.get(arxiv_id)
            await indexer.index_paper_chunks(arxiv_id, chunks, embeddings=embeddings)

    async def _embed_corpus(
        self, config: ExperimentConfig, chunks_by_paper: list[tuple[str, list[Chunk]]]
    ) -> dict[str, list[list[float]]]:
        if config.retrieval_mode != "vector":
            return {}

        # collect every chunk's text from every paper into one flat list
        all_texts = []
        for _, chunks in chunks_by_paper:
            for chunk in chunks:
                all_texts.append(chunk.content)

        if not all_texts:
            return {}

        # One embed call for everything, not one call per chunk - much
        # cheaper and faster this way.
        start = time.perf_counter()
        all_embeddings, tokens = await self._embedding_client.embed(all_texts)
        self._corpus_embedding_latency_ms += (time.perf_counter() - start) * 1000
        self._embedding_tokens += tokens

        # all_embeddings is one flat list for every paper combined, so we
        # need to cut it back into pieces and give each paper its own slice
        # in the same order we put the chunks in.
        embeddings_by_paper: dict[str, list[list[float]]] = {}
        cursor = 0
        for arxiv_id, chunks in chunks_by_paper:
            embeddings_by_paper[arxiv_id] = all_embeddings[cursor : cursor + len(chunks)]
            cursor += len(chunks)

        return embeddings_by_paper

    async def _run_queries(
        self, retriever: Retriever, golden_queries: list[GoldenQuery], top_k: int
    ) -> tuple[dict[str, list[SearchHit]], list[float]]:
        hits_by_query: dict[str, list[SearchHit]] = {}
        latencies_ms: list[float] = []

        for golden in golden_queries:
            start = time.perf_counter()
            hits_by_query[golden.query] = await retriever.search(golden.query, top_k)
            latencies_ms.append((time.perf_counter() - start) * 1000)

        # VectorRetriever keeps count of how many tokens it used to embed
        # each query. Bm25Retriever does not have this attribute at all,
        # so we check for it first instead of assuming it is there.
        if hasattr(retriever, "tokens_used"):
            self._embedding_tokens += retriever.tokens_used

        return hits_by_query, latencies_ms

    async def _index_size_bytes(self, index_name: str) -> int:
        stats = await self._opensearch_client.indices.stats(index=index_name)
        return stats["indices"][index_name]["total"]["store"]["size_in_bytes"]

    def _build_ops_metrics(
        self, index_size_bytes: int, latencies_ms: list[float], embedding_model: str | None
    ) -> OpsMetrics:
        if embedding_model in EMBEDDING_MODEL_SPECS:
            price_per_million = EMBEDDING_MODEL_SPECS[embedding_model]["price_per_million_tokens_usd"]
        else:
            price_per_million = 0.0

        estimated_cost = round(self._embedding_tokens / 1_000_000 * price_per_million, 6)

        if latencies_ms:
            total_latency = 0.0
            for latency in latencies_ms:
                total_latency = total_latency + latency
            avg_latency_ms = round(total_latency / len(latencies_ms), 2)
        else:
            avg_latency_ms = 0.0

        return OpsMetrics(
            avg_latency_ms=avg_latency_ms,
            index_size_bytes=index_size_bytes,
            embedding_tokens=self._embedding_tokens,
            estimated_embedding_cost_usd=estimated_cost,
            # This is only the time to embed the corpus while indexing.
            # The time to embed each query during search is already part
            # of avg_latency_ms above, since that is really part of how
            # long one query takes.
            embedding_latency_ms=round(self._corpus_embedding_latency_ms, 2),
        )
