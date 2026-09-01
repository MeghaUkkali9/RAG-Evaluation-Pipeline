"""Checks if two experiment runs really differ, or if the gap could just be noise.

Usage:
    python -m scripts.compare_significance --run-a section_aware_academic --run-b academic_openai_vector
    python -m scripts.compare_significance --run-a section_aware_academic --run-b academic_openai_vector --metric recall_at_k_section
"""

import argparse

from src.database import SessionLocal
from src.models.experiment_run import ExperimentRun
from src.repositories.ExperimentRunRepository import ExperimentRunRepository
from src.services.EvaluationService.significance import bootstrap_compare

# Maps a RetrievalMetrics field name to the PerQueryResult field it comes
# from, so the same per-query data is used for both the summary metric and
# this significance check.
METRIC_FIELDS = {
    "recall_at_k": "paper_hit",
    "mrr": "paper_reciprocal_rank",
    "recall_at_k_section": "section_hit",
    "mrr_section": "section_reciprocal_rank",
}


def _latest_run(runs: list[ExperimentRun], name: str) -> ExperimentRun:
    matches = []
    for run in runs:
        if run.name == name:
            matches.append(run)

    if not matches:
        raise ValueError(f"No experiment run found with name '{name}'")

    return matches[-1]  # list_all() gives oldest first, so the last match is the newest run


def _aligned_scores(run_a: ExperimentRun, run_b: ExperimentRun, field: str) -> tuple[list[float], list[float]]:
    per_query_a = {}
    for row in run_a.metrics.get("per_query", []):
        per_query_a[row["query"]] = row

    per_query_b = {}
    for row in run_b.metrics.get("per_query", []):
        per_query_b[row["query"]] = row

    # only compare questions that show up in both runs
    common_queries = []
    for query in per_query_a:
        if query in per_query_b:
            common_queries.append(query)
    common_queries.sort()

    if len(common_queries) < len(per_query_a) or len(common_queries) < len(per_query_b):
        print(
            f"WARNING: the two runs don't share the exact same query set "
            f"({len(common_queries)} shared out of {len(per_query_a)} / {len(per_query_b)}) - "
            "were they run against the same evaluation/golden_dataset.json?"
        )

    scores_a = []
    scores_b = []
    for query in common_queries:
        value_a = per_query_a[query].get(field)
        value_b = per_query_b[query].get(field)
        if value_a is None or value_b is None:
            continue  # happens for section-level fields when a query has no expected_section_title
        scores_a.append(float(value_a))
        scores_b.append(float(value_b))

    return scores_a, scores_b


def main(run_a_name: str, run_b_name: str, metric: str) -> None:
    session = SessionLocal()
    try:
        runs = ExperimentRunRepository(session).list_all()
    finally:
        session.close()

    run_a = _latest_run(runs, run_a_name)
    run_b = _latest_run(runs, run_b_name)

    if "per_query" not in run_a.metrics or "per_query" not in run_b.metrics:
        print(
            "One or both runs are from before per-query results were saved, so there is "
            "nothing to resample here - re-run them with the current code first."
        )
        return

    scores_a, scores_b = _aligned_scores(run_a, run_b, METRIC_FIELDS[metric])
    if not scores_a:
        print("No comparable queries found between the two runs for this metric.")
        return

    result = bootstrap_compare(scores_a, scores_b, metric_name=metric)

    print(f"{run_a_name:<28}{metric}: {result.mean_a}")
    print(f"{run_b_name:<28}{metric}: {result.mean_b}")
    print(f"difference (b - a): {result.mean_diff:+.4f}  [95% CI: {result.ci_low:+.4f}, {result.ci_high:+.4f}]")
    print(f"based on {result.n_queries} paired queries")

    if result.significant:
        print("-> significant: the confidence interval does not cross zero")
    else:
        print("-> NOT significant: this gap could just be noise at this sample size")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-a", required=True, help="Experiment name, treated as the baseline")
    parser.add_argument("--run-b", required=True, help="Experiment name being compared against run-a")
    parser.add_argument("--metric", choices=list(METRIC_FIELDS), default="recall_at_k_section")
    args = parser.parse_args()

    main(args.run_a, args.run_b, args.metric)
