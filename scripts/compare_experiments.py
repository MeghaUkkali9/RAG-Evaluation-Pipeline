"""Compare all recorded experiment runs.

Usage:
    python -m scripts.compare_experiments
"""

from src.database import SessionLocal
from src.repositories.ExperimentRunRepository import ExperimentRunRepository


def main() -> None:
    session = SessionLocal()
    try:
        runs = ExperimentRunRepository(session).list_all()
    finally:
        session.close()

    if not runs:
        print("No experiment runs recorded yet - run scripts.run_experiment first.")
        return

    print(
        f"{'name':<28}{'strategy':<24}{'recall@k':>10}{'mrr':>8}"
        f"{'sec_recall':>12}{'sec_mrr':>9}{'latency_ms':>12}{'index_mb':>10}"
    )

    for run in runs:
        strategy = run.config.get("chunking_strategy", "?")
        retrieval = run.metrics.get("retrieval", {})
        ops = run.metrics.get("ops", {})
        index_mb = ops.get("index_size_bytes", 0) / (1024 * 1024)

        print(
            f"{run.name:<28}{strategy:<24}"
            f"{retrieval.get('recall_at_k', 0):>10.2f}"
            f"{retrieval.get('mrr', 0):>8.2f}"
            f"{retrieval.get('recall_at_k_section', 0):>12.2f}"
            f"{retrieval.get('mrr_section', 0):>9.2f}"
            f"{ops.get('avg_latency_ms', 0):>12.1f}"
            f"{index_mb:>10.2f}"
        )

    if any("recall_at_k_section" not in r.metrics.get("retrieval", {}) for r in runs):
        print(
            "\nNote: some runs above predate the section-level metrics and show 0.00 for "
            "sec_recall/sec_mrr because that wasn't measured yet, not because it scored zero. "
            "Re-run those experiments to get real numbers."
        )


if __name__ == "__main__":
    main()
