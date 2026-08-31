"""Compare chunking strategies against an already-ingested paper.

Usage:
    python -m scripts.evaluate_chunking <arxiv_id>

The paper must already be ingested (POST /papers/{arxiv_id}/ingest) so its
raw text and sections are in Postgres - this script re-chunks that stored
data with each strategy, it doesn't re-download or re-parse the PDF.
"""

import argparse

from src.database import SessionLocal
from src.models.paper import Paper
from src.services.ChunkingService.evaluation import evaluate_chunks
from src.services.ChunkingService.schemas import ParsedDocument, Section
from src.services.ChunkingService.strategies import ChunkingStrategyName, build_chunking_strategy


def load_parsed_document(arxiv_id: str) -> tuple[Paper, ParsedDocument]:
    session = SessionLocal()
    try:
        paper = session.query(Paper).filter(Paper.arxiv_id == arxiv_id).one()
    finally:
        session.close()

    sections = [Section(**section) for section in paper.sections]
    return paper, ParsedDocument(raw_text=paper.raw_text, sections=sections)


def compare_strategies(arxiv_id: str) -> None:
    paper, parsed = load_parsed_document(arxiv_id)

    print(f"{'strategy':<24}{'chunks':>8}{'avg_words':>11}{'min':>6}{'max':>6}{'below_min':>11}{'coverage':>10}")

    for strategy_name in ChunkingStrategyName:
        chunker = build_chunking_strategy(strategy_name)
        chunks = chunker.chunk(paper.title, paper.abstract, parsed)
        metrics = evaluate_chunks(
            strategy_name=strategy_name.value,
            parsed=parsed,
            chunks=chunks,
            target_min_words=100,
        )

        print(
            f"{metrics.strategy_name:<24}"
            f"{metrics.chunk_count:>8}"
            f"{metrics.avg_words_per_chunk:>11}"
            f"{metrics.min_words_per_chunk:>6}"
            f"{metrics.max_words_per_chunk:>6}"
            f"{metrics.chunks_below_target:>11}"
            f"{metrics.coverage_ratio:>10}"
        )


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument("arxiv_id")
    args = arg_parser.parse_args()

    compare_strategies(args.arxiv_id)
