from typing import Literal

from pydantic import BaseModel

from src.services.ChunkingService.strategies import ChunkingStrategyName


class GoldenQuery(BaseModel):
    query: str
    arxiv_id: str
    expected_section_title: str | None = None
    source: Literal["llm_draft", "human"] = "llm_draft"


class ExperimentConfig(BaseModel):
    """One point in the experiment space. Only the fields with a real
    implementation behind them are wired up today - the rest are reserved
    so later phases (embeddings, hybrid retrieval, reranking, generation)
    extend this same config instead of inventing a new one."""

    name: str
    chunking_strategy: ChunkingStrategyName
    retrieval_mode: Literal["bm25"] = "bm25"  # "vector" | "hybrid" land in later phases
    top_k: int = 5
    use_reranker: bool = False  # reserved, not wired yet
    embedding_model: str | None = None  # reserved, not wired yet
    generation_model: str | None = None  # reserved, not wired yet


class RetrievalMetrics(BaseModel):
    recall_at_k: float
    mrr: float
    total_queries: int
    # Same idea as recall_at_k/mrr, but a hit only counts if it also comes
    # from the expected section - not just the right paper. Paper-level
    # recall saturates fast on a small corpus (BM25 usually finds *a*
    # chunk from the right paper regardless of chunk boundaries), so this
    # is what actually discriminates between chunking strategies.
    recall_at_k_section: float
    mrr_section: float
    # Queries without an expected_section_title don't contribute to the
    # section-level numbers above - this says how many did, since it's a
    # different (usually smaller) denominator than total_queries.
    section_eval_count: int


class OpsMetrics(BaseModel):
    avg_latency_ms: float
    index_size_bytes: int


class ExperimentResult(BaseModel):
    config: ExperimentConfig
    retrieval: RetrievalMetrics
    ops: OpsMetrics
