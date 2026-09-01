from typing import Literal

from pydantic import BaseModel

from src.services.ChunkingService.strategies import ChunkingStrategyName


class GoldenQuery(BaseModel):
    query: str
    arxiv_id: str
    expected_section_title: str | None = None
    source: Literal["llm_draft", "human"] = "llm_draft"


class ExperimentConfig(BaseModel):
    """One setup we want to test. Only the fields that actually do
    something are wired up right now - the rest are here as placeholders,
    so later work (embeddings, hybrid search, reranking, generation) can
    reuse this same config instead of us making a new one each time."""

    name: str
    chunking_strategy: ChunkingStrategyName
    retrieval_mode: Literal["bm25", "vector"] = "bm25"  # "hybrid" comes later
    top_k: int = 5
    use_reranker: bool = False  # not used yet
    embedding_model: str | None = None  # needed when retrieval_mode == "vector"
    generation_model: str | None = None  # not used yet


class RetrievalMetrics(BaseModel):
    recall_at_k: float
    mrr: float
    total_queries: int
    # Same as recall_at_k/mrr, but this time a hit only counts if it comes
    # from the right section, not just the right paper. On a small corpus,
    # paper-level recall gets too easy fast - BM25 usually finds *some*
    # chunk from the right paper no matter how it was cut. This section
    # score is what actually shows a difference between chunking strategies.
    recall_at_k_section: float
    mrr_section: float
    # Not every query has an expected_section_title, so the section numbers
    # above are averaged over fewer queries than total_queries. This says
    # how many actually went into that average.
    section_eval_count: int


class PerQueryResult(BaseModel):
    """The raw result for one question, before we average it into
    RetrievalMetrics. We keep this too, next to the summary numbers, so
    later we can check significance or look at which questions keep
    failing, without running retrieval all over again."""

    query: str
    arxiv_id: str
    paper_hit: bool
    paper_reciprocal_rank: float
    section_hit: bool | None = None
    section_reciprocal_rank: float | None = None


class OpsMetrics(BaseModel):
    avg_latency_ms: float
    index_size_bytes: int
    # Adds up tokens from embedding the corpus (at indexing time) and
    # embedding each query (at search time) into one number, not two.
    # Stays 0 for a BM25 run since no embedding happens there.
    embedding_tokens: int = 0
    estimated_embedding_cost_usd: float = 0.0
    embedding_latency_ms: float = 0.0


class ExperimentResult(BaseModel):
    config: ExperimentConfig
    retrieval: RetrievalMetrics
    ops: OpsMetrics
    per_query: list[PerQueryResult]
