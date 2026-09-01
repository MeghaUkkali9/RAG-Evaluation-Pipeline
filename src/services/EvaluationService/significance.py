import random

from pydantic import BaseModel


class SignificanceResult(BaseModel):
    metric: str
    mean_a: float
    mean_b: float
    mean_diff: float  # b - a
    ci_low: float
    ci_high: float
    n_queries: int
    # Only true if the confidence interval does not cross zero. This means
    # resampling the same queries again and again keeps favoring the same
    # side, so the gap is not just because of which queries happened to
    # land in this golden set.
    significant: bool


def _average(values: list[float]) -> float:
    total = 0.0
    for value in values:
        total = total + value
    return total / len(values)


def bootstrap_compare(
    scores_a: list[float],
    scores_b: list[float],
    metric_name: str,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> SignificanceResult:
    """A paired bootstrap significance test. scores_a[i] and scores_b[i]
    need to be the same query i, just scored under two different setups
    (for example one number per query: 1.0/0.0 for hit or miss, or a
    reciprocal rank for MRR).

    What this does: it picks queries at random (with repeats allowed) many
    times, and each time it recomputes the average score for both sides,
    then looks at (mean_b - mean_a). If, after doing this many times, 95%
    of those differences stay on the same side of zero, the gap is
    probably real and not just luck from which questions we happened to
    put in the golden set. Just looking at "0.68 vs 0.56, looks like a real
    gap" is not the same thing as actually checking this.
    """
    if len(scores_a) != len(scores_b):
        raise ValueError("scores_a and scores_b must be paired and the same length")
    if not scores_a:
        raise ValueError("no queries to compare")

    n = len(scores_a)
    rng = random.Random(seed)
    diffs = []

    for _ in range(n_resamples):
        # pick n queries at random - the same one can get picked more than once
        indices = []
        for _ in range(n):
            indices.append(rng.randrange(n))

        resampled_a_values = []
        resampled_b_values = []
        for i in indices:
            resampled_a_values.append(scores_a[i])
            resampled_b_values.append(scores_b[i])

        resampled_a = _average(resampled_a_values)
        resampled_b = _average(resampled_b_values)
        diffs.append(resampled_b - resampled_a)

    diffs.sort()
    alpha = 1 - confidence
    ci_low = diffs[int((alpha / 2) * n_resamples)]
    ci_high = diffs[int((1 - alpha / 2) * n_resamples) - 1]

    if ci_low <= 0 <= ci_high:
        significant = False
    else:
        significant = True

    return SignificanceResult(
        metric=metric_name,
        mean_a=round(_average(scores_a), 4),
        mean_b=round(_average(scores_b), 4),
        mean_diff=round(_average(scores_b) - _average(scores_a), 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        n_queries=n,
        significant=significant,
    )
