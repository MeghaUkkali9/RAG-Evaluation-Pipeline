from statistics import median

from pydantic import BaseModel

from src.services.ChunkingService.schemas import Chunk, ParsedDocument


class ChunkingMetrics(BaseModel):
    """A simple, structural look at what a chunking strategy produced. This
    does not measure if the chunks are actually good for retrieval - that
    needs real queries and an embedding model, which come later. This just
    answers a cheaper question first: does the output even look right (not
    too many tiny pieces, not chunks way too big, not losing text)?
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
    # This is indexed_word_count / source_word_count. Being above 1.0 is
    # normal and fine - it comes from the title/section text we add to
    # each chunk, plus overlap between windows. If it were much higher
    # than 1.0, that would mean too much duplicate text from an overlap
    # that is too big compared to the chunk size.
    coverage_ratio: float


def evaluate_chunks(
    strategy_name: str,
    parsed: ParsedDocument,
    chunks: list[Chunk],
    target_min_words: int,
) -> ChunkingMetrics:
    word_counts = []
    for chunk in chunks:
        word_counts.append(len(chunk.content.split()))

    if not word_counts:
        word_counts = [0]

    source_word_count = len(parsed.raw_text.split())

    # add up every chunk's word count, and count how many chunks are
    # smaller than the target, in one pass
    indexed_word_count = 0
    chunks_below_target = 0
    for count in word_counts:
        indexed_word_count = indexed_word_count + count
        if count < target_min_words:
            chunks_below_target = chunks_below_target + 1

    avg_words_per_chunk = round(indexed_word_count / len(word_counts), 1)

    if source_word_count > 0:
        coverage_ratio = round(indexed_word_count / source_word_count, 2)
    else:
        coverage_ratio = 0.0

    return ChunkingMetrics(
        strategy_name=strategy_name,
        chunk_count=len(chunks),
        avg_words_per_chunk=avg_words_per_chunk,
        median_words_per_chunk=median(word_counts),
        min_words_per_chunk=min(word_counts),
        max_words_per_chunk=max(word_counts),
        chunks_below_target=chunks_below_target,
        source_word_count=source_word_count,
        indexed_word_count=indexed_word_count,
        coverage_ratio=coverage_ratio,
    )
