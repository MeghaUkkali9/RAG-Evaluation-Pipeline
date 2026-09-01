import json
from pathlib import Path

from src.services.EvaluationService.schemas import GoldenQuery


def load_golden_queries(path: Path) -> list[GoldenQuery]:
    data = json.loads(path.read_text())

    golden_queries = []
    for item in data:
        golden_queries.append(GoldenQuery(**item))

    return golden_queries
