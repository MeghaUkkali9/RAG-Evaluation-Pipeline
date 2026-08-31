from src.services.EvaluationService.schemas import GoldenQuery, RetrievalMetrics
from src.services.RetrievalService.schemas import SearchHit


def evaluate_retrieval(
    golden_queries: list[GoldenQuery],
    hits_by_query: dict[str, list[SearchHit]],
    top_k: int,
) -> RetrievalMetrics:
    """Computes two views of the same hits:

    - Paper-level: a hit counts as relevant if it comes from the paper the
      golden query names.
    - Section-level: a hit only counts if it's also from the expected
      section. Uses substring matching rather than exact equality, since a
      merged section's title is a "+"-joined combination (e.g.
      "Limitations + Related Work") and should still match a query whose
      expected_section_title is just "Limitations".
    """
    hit_found = []
    reciprocal_ranks = []
    section_hit_found = []
    section_reciprocal_ranks = []

    for golden in golden_queries:
        hits = hits_by_query[golden.query][:top_k]

        paper_ranks = [rank for rank, hit in enumerate(hits, start=1) if hit.arxiv_id == golden.arxiv_id]
        hit_found.append(bool(paper_ranks))
        reciprocal_ranks.append(1 / paper_ranks[0] if paper_ranks else 0.0)

        if golden.expected_section_title:
            section_ranks = [
                rank
                for rank, hit in enumerate(hits, start=1)
                if hit.arxiv_id == golden.arxiv_id and golden.expected_section_title in hit.section_title
            ]
            section_hit_found.append(bool(section_ranks))
            section_reciprocal_ranks.append(1 / section_ranks[0] if section_ranks else 0.0)

    total = len(golden_queries)
    section_total = len(section_hit_found)

    return RetrievalMetrics(
        recall_at_k=round(sum(hit_found) / total, 3) if total else 0.0,
        mrr=round(sum(reciprocal_ranks) / total, 3) if total else 0.0,
        total_queries=total,
        recall_at_k_section=round(sum(section_hit_found) / section_total, 3) if section_total else 0.0,
        mrr_section=round(sum(section_reciprocal_ranks) / section_total, 3) if section_total else 0.0,
        section_eval_count=section_total,
    )
