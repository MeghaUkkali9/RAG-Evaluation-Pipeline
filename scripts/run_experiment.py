"""Runs one experiment (a chunking strategy plus a retrieval mode) and saves the result.

Usage:
    python -m scripts.run_experiment --strategy section_aware_400 --experiment-name baseline_400
    python -m scripts.run_experiment --strategy section_aware_academic --experiment-name academic_vector --retrieval-mode vector
"""

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from opensearchpy import AsyncOpenSearch

from src.config import get_settings
from src.database import SessionLocal
from src.repositories.ExperimentRunRepository import ExperimentRunRepository
from src.services.ChunkingService.strategies import ChunkingStrategyName
from src.services.EmbeddingService.client import EmbeddingClient
from src.services.EmbeddingService.factory import create_embedding_client
from src.services.EvaluationService.golden_dataset import load_golden_queries
from src.services.EvaluationService.runner import ExperimentRunner
from src.services.EvaluationService.schemas import ExperimentConfig

load_dotenv()

GOLDEN_DATASET_PATH = Path("evaluation/golden_dataset.json")


async def run(
    strategy: ChunkingStrategyName,
    experiment_name: str,
    top_k: int,
    retrieval_mode: str,
) -> None:
    settings = get_settings()
    golden_queries = load_golden_queries(GOLDEN_DATASET_PATH)

    opensearch_client = AsyncOpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=False,
    )
    session = SessionLocal()

    embedding_client: EmbeddingClient | None = None
    embedding_model: str | None = None
    if retrieval_mode == "vector":
        embedding_client = create_embedding_client(settings)
        embedding_model = settings.embedding_model

    try:
        runner = ExperimentRunner(
            opensearch_client=opensearch_client, session=session, embedding_client=embedding_client
        )
        config = ExperimentConfig(
            name=experiment_name,
            chunking_strategy=strategy,
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            embedding_model=embedding_model,
        )
        result = await runner.run(config, golden_queries)

        ExperimentRunRepository(session).save_result(result)
        print(result.model_dump_json(indent=2))
    finally:
        session.close()
        await opensearch_client.close()


if __name__ == "__main__":
    strategy_choices = []
    for strategy in ChunkingStrategyName:
        strategy_choices.append(strategy.value)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", required=True, choices=strategy_choices)
    parser.add_argument("--experiment-name", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--retrieval-mode", choices=["bm25", "vector"], default="bm25")
    args = parser.parse_args()

    asyncio.run(
        run(ChunkingStrategyName(args.strategy), args.experiment_name, args.top_k, args.retrieval_mode)
    )
