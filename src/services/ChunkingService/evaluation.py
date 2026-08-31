from statistics import mean, median

from pydantic import BaseModel

from src.services.ChunkingService.schemas import Chunk, ParsedDocument


class ChunkingMetrics(BaseModel):
    """Structural, retrieval-agnostic view of a chunking strategy's output.

    This doesn't measure whether the chunks are good for retrieval - that
    needs real queries and an embedding model, which come later. It answers
    the cheaper question first: does the output even look sane (not too
    many tiny fragments, not wildly oversized chunks, not losing text)?
    """

    strategy_name: str
    chunk_count: int
    avg_words_per_chunk: float
    median_words_per_chunk: float
    min_words_per_chunk: int
    max_words_per_chunk: int
    chunks_below_target: int
    source_word_count: int
    indexed_word_count: int
    # indexed_word_count / source_word_count. Above 1.0 is expected and
    # healthy - it's the injected title/section headers plus sliding-window
    # overlap. A number many times higher than 1.0 would signal excessive
    # duplication from overlap that's too large relative to chunk size.
    coverage_ratio: float


def evaluate_chunks(
    strategy_name: str,
    parsed: ParsedDocument,
    chunks: list[Chunk],
    target_min_words: int,
) -> ChunkingMetrics:
    word_counts = [len(chunk.content.split()) for chunk in chunks]

    if not word_counts:
        word_counts = [0]

    source_word_count = len(parsed.raw_text.split())
    indexed_word_count = sum(word_counts)

    return ChunkingMetrics(
        strategy_name=strategy_name,
        chunk_count=len(chunks),
        avg_words_per_chunk=round(mean(word_counts), 1),
        median_words_per_chunk=median(word_counts),
        min_words_per_chunk=min(word_counts),
        max_words_per_chunk=max(word_counts),
        chunks_below_target=sum(1 for count in word_counts if count < target_min_words),
        source_word_count=source_word_count,
        indexed_word_count=indexed_word_count,
        coverage_ratio=round(indexed_word_count / source_word_count, 2) if source_word_count else 0.0,
    )
