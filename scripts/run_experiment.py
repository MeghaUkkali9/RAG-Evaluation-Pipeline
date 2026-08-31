"""Run one chunking-strategy x BM25 experiment and save the result.

Usage:
    python -m scripts.run_experiment --strategy section_aware_400 --experiment-name baseline_400
"""

import argparse
import asyncio
from pathlib import Path

from opensearchpy import AsyncOpenSearch

from src.config import get_settings
from src.database import SessionLocal
from src.repositories.ExperimentRunRepository import ExperimentRunRepository
from src.services.ChunkingService.strategies import ChunkingStrategyName
from src.services.EvaluationService.golden_dataset import load_golden_queries
from src.services.EvaluationService.runner import ExperimentRunner
from src.services.EvaluationService.schemas import ExperimentConfig

GOLDEN_DATASET_PATH = Path("evaluation/golden_dataset.json")


async def run(strategy: ChunkingStrategyName, experiment_name: str, top_k: int) -> None:
    settings = get_settings()
    golden_queries = load_golden_queries(GOLDEN_DATASET_PATH)

    opensearch_client = AsyncOpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=False,
    )
    session = SessionLocal()

    try:
        runner = ExperimentRunner(opensearch_client=opensearch_client, session=session)
        config = ExperimentConfig(name=experiment_name, chunking_strategy=strategy, top_k=top_k)
        result = await runner.run(config, golden_queries)

        ExperimentRunRepository(session).save_result(result)
        print(result.model_dump_json(indent=2))
    finally:
        session.close()
        await opensearch_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", required=True, choices=[s.value for s in ChunkingStrategyName])
    parser.add_argument("--experiment-name", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(run(ChunkingStrategyName(args.strategy), args.experiment_name, args.top_k))
