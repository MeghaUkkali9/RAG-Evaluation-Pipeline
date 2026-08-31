"""Draft a golden query set from ingested papers using an LLM.

Usage:
    python -m scripts.generate_golden_dataset

Writes evaluation/golden_dataset.json. REVIEW THIS FILE BY HAND before
trusting any experiment results computed against it - LLM-drafted questions
can be too easy, ambiguous, or point at the wrong section.
"""

import difflib
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.database import SessionLocal
from src.models.paper import Paper

load_dotenv()

OUTPUT_PATH = Path("evaluation/golden_dataset.json")
QUESTIONS_PER_PAPER = 5
SECTION_EXCERPT_WORDS = 120

PROMPT_TEMPLATE = """You are drafting evaluation questions for a RAG system that indexes academic papers. \
These questions will be used to test whether the system retrieves the right section for a query, so \
quality matters more than quantity.

Paper title: {title}
Abstract: {abstract}

Sections:
{sections_block}

Write {n} questions a researcher might realistically ask that this specific paper answers well. Rules:
- Ground each question in a specific detail from ONE section's content below, not just its title, and not
  something already fully stated in the abstract.
- Do not write questions that are just a rephrasing of the abstract - BM25 finds those trivially regardless
  of chunking quality, so they don't tell us anything useful.
- Do not write questions so generic that other papers on a similar topic could also answer them
  (avoid "What is attention?"; prefer "What attention variant does this paper propose and why?").
- Spread the questions across different sections rather than clustering on the largest one - include at
  least one question about a smaller section (e.g. limitations, related work, a specific design choice),
  if such a section exists.
- Vary difficulty: mix concrete factual questions (numbers, dataset names, specific terms) with conceptual
  ones (why a design choice was made, what a limitation is).

For each question, name the exact section title above (copy it exactly) that most directly answers it.

Respond with JSON: {{"questions": [{{"question": "...", "expected_section_title": "..."}}]}}
"""


def _build_sections_block(paper: Paper) -> str:
    lines = []
    for section in paper.sections:
        excerpt = " ".join(section["content"].split()[:SECTION_EXCERPT_WORDS])
        lines.append(f"- {section['title']}: {excerpt}")
    return "\n".join(lines)


def _resolve_section_title(expected_title: str, real_titles: set[str]) -> tuple[str, bool]:
    """Returns (resolved_title, was_corrected). Two distinct failure modes
    get auto-corrected here, each checked with a signal specific to it
    rather than one loose fuzzy-match threshold:

    - Typos: source PDFs regularly have them in their own headings (Docling
      copies them verbatim), and the LLM tends to "fix" the spelling when it
      references one. A high-similarity fuzzy match catches this safely.
    - Truncation: the LLM sometimes shortens a long numbered heading (e.g.
      "3 Problems of RNNs" for the real "3 Problems of RNNs: Vanishing &
      Exploding Gradients"). This drops the fuzzy-match ratio too low to use
      a single lower cutoff without risking false matches to unrelated
      sections, so it's checked directly via prefix containment instead.

    A title matching neither case is left as-is for manual review."""
    if expected_title in real_titles:
        return expected_title, False

    prefix_matches = sorted(
        (title for title in real_titles if title.lower().startswith(expected_title.lower())),
        key=len,
    )
    if prefix_matches:
        return prefix_matches[0], True

    close_matches = difflib.get_close_matches(expected_title, real_titles, n=1, cutoff=0.8)
    if close_matches:
        return close_matches[0], True

    return expected_title, False


def draft_questions_for_paper(client: OpenAI, paper: Paper) -> list[dict]:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    title=paper.title,
                    abstract=paper.abstract,
                    sections_block=_build_sections_block(paper),
                    n=QUESTIONS_PER_PAPER,
                ),
            }
        ],
    )

    return json.loads(response.choices[0].message.content)["questions"]


def main() -> None:
    client = OpenAI()
    session = SessionLocal()

    try:
        papers = session.query(Paper).all()
    finally:
        session.close()

    if not papers:
        print("No ingested papers found - ingest some via POST /papers/{arxiv_id}/ingest first.")
        return

    golden_queries = []
    mismatched_count = 0

    for paper in papers:
        try:
            drafted = draft_questions_for_paper(client, paper)
        except Exception as e:
            print(f"Failed to draft questions for {paper.arxiv_id}: {e}")
            continue

        section_titles = {section["title"] for section in paper.sections}

        for item in drafted:
            drafted_title = item.get("expected_section_title")
            resolved_title, was_corrected = _resolve_section_title(drafted_title, section_titles)

            if was_corrected:
                print(f"  Auto-corrected [{paper.arxiv_id}]: '{drafted_title}' -> '{resolved_title}'")
            elif resolved_title not in section_titles:
                mismatched_count += 1
                print(
                    f"  WARNING [{paper.arxiv_id}]: expected_section_title "
                    f"'{drafted_title}' doesn't match any real section "
                    f"{sorted(section_titles)} - check this one during review."
                )

            golden_queries.append(
                {
                    "query": item["question"],
                    "arxiv_id": paper.arxiv_id,
                    "expected_section_title": resolved_title,
                    "source": "llm_draft",
                }
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(golden_queries, indent=2))

    print(f"Drafted {len(golden_queries)} questions across {len(papers)} papers -> {OUTPUT_PATH}")
    if mismatched_count:
        print(f"{mismatched_count} question(s) have a section mismatch - see warnings above, fix during review.")
    print("Review and edit this file by hand before trusting any experiment results computed against it.")


if __name__ == "__main__":
    main()
