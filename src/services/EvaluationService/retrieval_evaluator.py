from src.services.EvaluationService.schemas import GoldenQuery, PerQueryResult, RetrievalMetrics
from src.services.RetrievalService.schemas import SearchHit


def evaluate_retrieval(
    golden_queries: list[GoldenQuery],
    hits_by_query: dict[str, list[SearchHit]],
    top_k: int,
) -> tuple[RetrievalMetrics, list[PerQueryResult]]:
    """Looks at the same hits in two ways paper-level and section-level
    (see PerQueryResult / RetrievalMetrics for why) and gives back the raw
    per-query results together with the averaged numbers the averaged
    numbers are just summary and the per-query list is the real evidence.

    For the section-level check, I use "is this title inside that title"
    instead of an exact match because a merged section's title is a few
    titles joined with "+" (like "Limitations + Related Work") and it
    should still count as a match for a query asking about "Limitations".
    """
    per_query: list[PerQueryResult] = []

    for golden in golden_queries:
        hits = hits_by_query[golden.query][:top_k]

        # walk through the hits in order, and remember the rank (1, 2, 3...)
        # of the first one that is from the right paper
        paper_hit_rank = None
        rank = 0
        for hit in hits:
            rank = rank + 1
            if hit.arxiv_id == golden.arxiv_id and paper_hit_rank is None:
                paper_hit_rank = rank

        if paper_hit_rank is not None:
            paper_hit = True
            paper_rr = 1 / paper_hit_rank
        else:
            paper_hit = False
            paper_rr = 0.0

        # do the same thing again, but only if this query has a section we
        # expect it to answer from
        section_hit = None
        section_rr = None
        if golden.expected_section_title:
            section_hit_rank = None
            rank = 0
            for hit in hits:
                rank = rank + 1
                is_right_paper = hit.arxiv_id == golden.arxiv_id
                is_right_section = golden.expected_section_title in hit.section_title
                if is_right_paper and is_right_section and section_hit_rank is None:
                    section_hit_rank = rank

            if section_hit_rank is not None:
                section_hit = True
                section_rr = 1 / section_hit_rank
            else:
                section_hit = False
                section_rr = 0.0

        per_query.append(
            PerQueryResult(
                query=golden.query,
                arxiv_id=golden.arxiv_id,
                paper_hit=paper_hit,
                paper_reciprocal_rank=paper_rr,
                section_hit=section_hit,
                section_reciprocal_rank=section_rr,
            )
        )

    total = len(per_query)

    # add up hits and reciprocal ranks across every query
    paper_hit_count = 0
    paper_rr_sum = 0.0
    for result in per_query:
        if result.paper_hit:
            paper_hit_count = paper_hit_count + 1
        paper_rr_sum = paper_rr_sum + result.paper_reciprocal_rank

    if total > 0:
        recall_at_k = round(paper_hit_count / total, 3)
        mrr = round(paper_rr_sum / total, 3)
    else:
        recall_at_k = 0.0
        mrr = 0.0

    # same thing again, but only counting queries that had a section to check
    section_total = 0
    section_hit_count = 0
    section_rr_sum = 0.0
    for result in per_query:
        if result.section_hit is None:
            continue
        section_total = section_total + 1
        if result.section_hit:
            section_hit_count = section_hit_count + 1
        section_rr_sum = section_rr_sum + result.section_reciprocal_rank

    if section_total > 0:
        recall_at_k_section = round(section_hit_count / section_total, 3)
        mrr_section = round(section_rr_sum / section_total, 3)
    else:
        recall_at_k_section = 0.0
        mrr_section = 0.0

    metrics = RetrievalMetrics(
        recall_at_k=recall_at_k,
        mrr=mrr,
        total_queries=total,
        recall_at_k_section=recall_at_k_section,
        mrr_section=mrr_section,
        section_eval_count=section_total,
    )

    return metrics, per_query
