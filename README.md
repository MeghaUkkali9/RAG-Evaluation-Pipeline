# RAG Evaluation Pipeline for arXiv Papers

This project builds a RAG (Retrieval-Augmented Generation) pipeline for academic papers from arXiv, and includes a framework to test and compare different chunking and retrieval choices with real numbers, not guesses.

## What it does

1. **Fetch** — downloads a paper's metadata and PDF from arXiv, given an arXiv ID.
2. **Parse** — uses [Docling](https://github.com/DS4SD/docling) to parse the PDF and detect its real sections (Introduction, Method, Results, etc.), not just raw text.
3. **Chunk** — splits the paper into chunks along section boundaries, not at random word counts. Small sections get merged, big sections get split, so no chunk is too small or too big.
4. **Index** — stores the chunks in [OpenSearch](https://opensearch.org/), for both keyword search (BM25) and vector search.
5. **Retrieve** — searches the index with BM25, embeddings, or both, and returns the best matching chunks for a query.

The data is stored in Postgres (paper metadata, raw text, sections) and OpenSearch (chunks for search).

## Why this project is more than "call an LLM API"

Most simple RAG projects just pick a chunk size and an embedding model and move on. This one is built to actually **test** those choices before committing to them:

- Multiple chunking strategies are built as swappable strategies (same interface, different config): fixed-size vs section-aware, with and without overlap, with and without extra context in each chunk.
- A small evaluation framework runs **controlled experiments** — only one setting changes at a time, so the comparison is fair.
- A golden set of test questions (drafted by an LLM from the real papers, then reviewed by hand, and git-tracked so results can always be traced back to the exact question set that produced them) is used to score each strategy with real retrieval metrics: recall@k and MRR, at both paper-level and section-level.
- Every experiment run is saved (config + results + the raw per-query outcome for every question) so different runs can be compared later, side by side.
- The framework also tracks latency, index size, tokens used, and estimated cost — not just "did it find the right answer".
- A gap between two runs is checked with a **bootstrap significance test**, not just by looking at whether one number is bigger than the other — a difference only counts as real if it survives resampling the questions many times.

Two real bugs were found and fixed while building this, using the framework itself:
- An OpenSearch timing bug where a fast experiment run queried the index before the documents were actually searchable yet, causing a false "0% recall" result for some strategies.
- The first version of the scoring only checked "did we find the right paper", which is too easy to pass on a small corpus. Adding a section-level check (did we find the right *part* of the paper) is what actually showed real differences between chunking strategies.

## What was actually measured

Example result comparing BM25 (keyword search) vs OpenAI embeddings, same chunking strategy, same papers:

| | BM25 | Vector (OpenAI) |
|---|---|---|
| recall@k | 0.92 | 0.94 |
| MRR | 0.89 | 0.94 |
| section-level recall | 0.56 | 0.70 |
| latency per query | ~17ms | ~255ms |
| index size | 1.4 MB | 16.2 MB |
| cost | $0 | ~$0.008 |

Vector search is ahead on every metric, and much slower and heavier on storage — but here is the honest part: when this gap is checked with the bootstrap significance test above (50 questions, 95% confidence), **none of these differences are statistically significant yet**. The direction is consistent (vector ahead on all four quality metrics), which is a mild positive sign, but 50 questions is not enough to be confident it is a real effect and not just which questions happened to be in the test set. Getting a confident answer here needs a bigger golden set (several hundred questions, not 50) — that is a known next step, not a finished result. This is exactly the kind of tradeoff, and the kind of honesty about what the data does and does not show, that the framework is built for.

## Tech stack

- **FastAPI** for the API
- **Docling** for PDF parsing
- **PostgreSQL** + **SQLAlchemy** for storing papers and experiment results
- **OpenSearch** for BM25 and vector (k-NN) search
- **OpenAI** for embeddings and for generating test questions
- **Docker Compose** for running Postgres + OpenSearch locally
- Plain **Protocol + factory** pattern for each service (fetch, chunk, index, retrieve, evaluate) instead of one big class doing everything — makes it easy to swap one piece (e.g. one chunking strategy, one retriever) without touching the rest.

## How to run it

```bash
# activate the virtual environment
source rag-pipline/bin/activate

# install dependencies
uv pip install -r requirments.txt

# start Postgres and OpenSearch
docker-compose up -d db opensearch

# run the API
uvicorn src.main:app --reload

# ingest a paper
curl -X POST http://localhost:8000/api/v1/papers/{arxiv_id}/ingest
```

Then, to run the evaluation:

```bash
# draft test questions from the ingested papers
python -m scripts.generate_golden_dataset

# review evaluation/golden_dataset.json by hand before trusting it

# run an experiment
python -m scripts.run_experiment --strategy section_aware_400 --experiment-name my_test

# same chunking strategy, but with vector search instead of BM25
python -m scripts.run_experiment --strategy section_aware_academic --experiment-name my_vector_test --retrieval-mode vector

# compare all experiments
python -m scripts.compare_experiments

# check if two experiments actually differ, or if it could be noise
python -m scripts.compare_significance --run-a my_test --run-b my_vector_test --metric recall_at_k_section
```

## What is not built yet

This project is still in progress. Not done yet:
- Hybrid search (combining BM25 + vector into one ranking)
- Reranking
- Answer generation (the actual "G" in RAG) and answer-quality scoring

These are the next steps, and the evaluation framework is already built so they can be tested the same controlled way once they exist.

## License

MIT — see [LICENSE](LICENSE).
