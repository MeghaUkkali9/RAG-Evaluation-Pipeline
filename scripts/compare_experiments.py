"""Compares all the experiment runs I have saved so far.

By default this only shows the latest run for each experiment name, so
re-running the same experiment (after fixing a bug, or changing a setting)
does not leave old, outdated rows cluttering up the table.

Usage:
    python -m scripts.compare_experiments
    python -m scripts.compare_experiments --all
"""

import argparse

from src.database import SessionLocal
from src.models.experiment_run import ExperimentRun
from src.repositories.ExperimentRunRepository import ExperimentRunRepository


def _latest_per_name(runs: list[ExperimentRun]) -> list[ExperimentRun]:
    # list_all() gives oldest first, so when we loop through and keep
    # overwriting by name, whatever is left at the end is the newest run.
    latest_by_name: dict[str, ExperimentRun] = {}
    for run in runs:
        latest_by_name[run.name] = run
    return list(latest_by_name.values())


def main(show_all: bool) -> None:
    session = SessionLocal()
    try:
        runs = ExperimentRunRepository(session).list_all()
    finally:
        session.close()

    if not runs:
        print("No experiment runs recorded yet - run scripts.run_experiment first.")
        return

    if not show_all:
        runs = _latest_per_name(runs)

    print(
        f"{'name':<28}{'strategy':<22}{'mode':<7}{'recall@k':>10}{'mrr':>7}"
        f"{'sec_recall':>12}{'sec_mrr':>9}{'latency_ms':>12}{'index_mb':>10}"
        f"{'tokens':>9}{'est_cost':>10}"
    )

    for run in runs:
        strategy = run.config.get("chunking_strategy", "?")
        mode = run.config.get("retrieval_mode", "bm25")
        retrieval = run.metrics.get("retrieval", {})
        ops = run.metrics.get("ops", {})
        index_mb = ops.get("index_size_bytes", 0) / (1024 * 1024)

        print(
            f"{run.name:<28}{strategy:<22}{mode:<7}"
            f"{retrieval.get('recall_at_k', 0):>10.2f}"
            f"{retrieval.get('mrr', 0):>7.2f}"
            f"{retrieval.get('recall_at_k_section', 0):>12.2f}"
            f"{retrieval.get('mrr_section', 0):>9.2f}"
            f"{ops.get('avg_latency_ms', 0):>12.1f}"
            f"{index_mb:>10.2f}"
            f"{ops.get('embedding_tokens', 0):>9}"
            f"{ops.get('estimated_embedding_cost_usd', 0):>10.5f}"
        )

    missing_section_metrics = False
    for run in runs:
        if "recall_at_k_section" not in run.metrics.get("retrieval", {}):
            missing_section_metrics = True

    if missing_section_metrics:
        print(
            "\nNote: some runs above are from before section-level metrics existed, so they "
            "show 0.00 for sec_recall/sec_mrr just because it was never measured, not because "
            "it actually scored zero. Re-run those to get real numbers."
        )

    if not show_all:
        print(f"\nShowing latest run per name ({len(runs)} shown). Use --all for full history.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Show every historical run, not just the latest per name")
    args = parser.parse_args()

    main(show_all=args.all)
