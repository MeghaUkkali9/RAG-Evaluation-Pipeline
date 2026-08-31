import time
from statistics import mean

from opensearchpy import AsyncOpenSearch
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.services.ChunkingService.schemas import ParsedDocument, Section
from src.services.ChunkingService.strategies import build_chunking_strategy
from src.services.EvaluationService.retrieval_evaluator import evaluate_retrieval
from src.services.EvaluationService.schemas import (
    ExperimentConfig,
    ExperimentResult,
    GoldenQuery,
    OpsMetrics,
)
from src.services.IndexingService.client import IndexingServiceClient
from src.services.RetrievalService.client import Bm25Retriever
from src.services.RetrievalService.schemas import SearchHit


class ExperimentRunner:
    """Runs one ExperimentConfig end to end: builds a fresh, dedicated
    OpenSearch index (never the live `paper_chunks` index), chunks and
    indexes every ingested paper with the configured strategy, runs the
    golden queries against it, and scores the result."""

    def __init__(self, opensearch_client: AsyncOpenSearch, session: Session):
        self._opensearch_client = opensearch_client
        self._session = session

    async def run(self, config: ExperimentConfig, golden_queries: list[GoldenQuery]) -> ExperimentResult:
        index_name = f"experiment_{config.name}"

        await self._reset_index(index_name)
        indexer = IndexingServiceClient(self._opensearch_client, index_name)
        await indexer.ensure_index()
        await self._index_all_papers(indexer, config)

        # OpenSearch doesn't make newly-indexed documents searchable until
        # its next background refresh (~1s by default). Without forcing one
        # here, a run that finishes indexing quickly (fewer, larger chunks)
        # can query before its own writes are visible, silently scoring
        # near-zero regardless of chunking quality.
        await self._opensearch_client.indices.refresh(index=index_name)

        retriever = Bm25Retriever(self._opensearch_client, index_name)
        hits_by_query, latencies_ms = await self._run_queries(retriever, golden_queries, config.top_k)

        retrieval_metrics = evaluate_retrieval(golden_queries, hits_by_query, config.top_k)
        ops_metrics = await self._collect_ops_metrics(index_name, latencies_ms)

        return ExperimentResult(config=config, retrieval=retrieval_metrics, ops=ops_metrics)

    async def _reset_index(self, index_name: str) -> None:
        # Delete-and-recreate rather than reusing whatever's already there,
        # so re-running the same experiment name is reproducible instead of
        # accumulating stale documents from a previous attempt.
        if await self._opensearch_client.indices.exists(index=index_name):
            await self._opensearch_client.indices.delete(index=index_name)

    async def _index_all_papers(self, indexer: IndexingServiceClient, config: ExperimentConfig) -> None:
        chunker = build_chunking_strategy(config.chunking_strategy)
        papers = self._session.query(Paper).all()

        for paper in papers:
            parsed = ParsedDocument(
                raw_text=paper.raw_text,
                sections=[Section(**section) for section in paper.sections],
            )
            chunks = chunker.chunk(paper.title, paper.abstract, parsed)
            await indexer.index_paper_chunks(paper.arxiv_id, chunks)

    async def _run_queries(
        self, retriever: Bm25Retriever, golden_queries: list[GoldenQuery], top_k: int
    ) -> tuple[dict[str, list[SearchHit]], list[float]]:
        hits_by_query: dict[str, list[SearchHit]] = {}
        latencies_ms: list[float] = []

        for golden in golden_queries:
            start = time.perf_counter()
            hits_by_query[golden.query] = await retriever.search(golden.query, top_k)
            latencies_ms.append((time.perf_counter() - start) * 1000)

        return hits_by_query, latencies_ms

    async def _collect_ops_metrics(self, index_name: str, latencies_ms: list[float]) -> OpsMetrics:
        stats = await self._opensearch_client.indices.stats(index=index_name)
        index_size_bytes = stats["indices"][index_name]["total"]["store"]["size_in_bytes"]

        return OpsMetrics(
            avg_latency_ms=round(mean(latencies_ms), 2) if latencies_ms else 0.0,
            index_size_bytes=index_size_bytes,
        )
