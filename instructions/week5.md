# Week 5 Instructions — Chunking, Embedding & Vector Store

## Overview

This week we move from raw data into the actual pipeline. The goal is to have a working retrieval system by end of week: cleaned JSON → chunks → embeddings → ChromaDB → query returns relevant results.

There are three parallel workstreams. Read your section carefully. The output of chunking feeds directly into embedding, and embedding feeds directly into the vector store — coordinate early, don't wait until you're blocked.

---

## Assignments

```
Sai     → Vector store (ChromaDB setup + ingestion + query interface)
Roland  → Chunking pipeline
Aleksia → Embedding pipeline, then support Sai on vector store when done
Patrick → Chunking pipeline (paired with Roland)
Monda   → Evaluation prep (question set + start on eval_retrieval.py)
```

---

## Workstream 1 — Chunking (Roland & Patrick)

### What you're doing

Taking the raw JSON files from `data/raw/` and splitting each document's `text` field into smaller chunks that can be individually embedded and retrieved. Output goes in `data/chunks/`.

### Why it matters

Chunk size is one of the most consequential design decisions in a RAG system and something we'll ablate later. Too large: irrelevant content gets retrieved alongside relevant content. Too small: you lose context. Start with sensible defaults and build it so the parameters are easy to change.

### Spec

**Libraries:** `tiktoken` for token counting. Use the `cl100k_base` encoding.

**Default parameters:**
- Chunk size: 400 tokens
- Overlap: 50 tokens

**Each output chunk object should look like this:**

```json
{
    "chunk_id": "fafsa_0_chunk_003",
    "text": "...chunk text...",
    "source": "https://...",
    "title": "FAFSA at Baruch College",
    "college": "Baruch College",
    "category": "financial_aid",
    "section": "",
    "chunk_index": 3,
    "total_chunks": 12,
    "scraped_date": "2025-04-04"
}
```

`chunk_id` format: `{source_filename}_{doc_index}_chunk_{chunk_index_zero_padded}`

All metadata fields (`college`, `category`, `source`, `title`, `section`, `scraped_date`) must be copied from the parent document onto every chunk.

**Script:** `chunker.py` at repo root. Should walk all files in `data/raw/` recursively and write output to `data/chunks/` mirroring the same subfolder structure. Make `chunk_size` and `overlap` easy-to-change constants at the top of the file.

**Edge case:** if a document's text is shorter than `chunk_size`, emit it as a single chunk.

### Definition of Done

- `chunker.py` runs cleanly over all of `data/raw/`
- Output files are in `data/chunks/` with correct structure
- Every chunk has all metadata fields populated
- Chunk size and overlap are constants, not hardcoded inline

### Push

```
git add chunker.py data/chunks/
git commit -m "add chunking pipeline"
git push
```

---

## Workstream 2 — Embedding (Aleksia — then support Sai when done)

### What you're doing

Taking the chunked JSON files from `data/chunks/` and producing a dense vector for each chunk's `text` field. Output goes in `data/embeddings/`.

**Coordinate with Roland and Patrick early** — ask them to share a sample output file so you can build against the right format before the full chunks are ready.

Once your embedder is running and output is pushed, move over to Sai's workstream and check in with him on where he needs support.

### Spec

**Library:** `sentence-transformers`. Model: `all-MiniLM-L6-v2` (384-dimensional vectors, fast, performs well on short passages).

Each output object should be the full chunk with an `embedding` field added:

```json
{
    "chunk_id": "fafsa_0_chunk_003",
    "text": "...",
    "source": "...",
    "title": "...",
    "college": "Baruch College",
    "category": "financial_aid",
    "section": "",
    "chunk_index": 3,
    "total_chunks": 12,
    "scraped_date": "2025-04-04",
    "embedding": [0.023, -0.145, ...]
}
```

**Script:** `embedder.py` at repo root. Make the model name a constant at the top of the file — we may swap models later as an ablation.

### Definition of Done

- `embedder.py` runs cleanly over all of `data/chunks/`
- Every output object has a valid `embedding` field
- Model name is a constant, not hardcoded inline
- Output files are in `data/embeddings/`

### Push

```
git add embedder.py data/embeddings/
git commit -m "add embedding pipeline"
git push
```

---

## Workstream 3 — Vector Store (Sai)

### What you're doing

Standing up ChromaDB, ingesting all embedded chunks, and writing a clean retrieval interface the rest of the team will use. Post in the group chat when the `retrieve()` interface is stable — others are building against it.

Aleksia will join you once embedding is done — post in the group chat when you have a good place for her to pick up.

### Spec

**Library:** `chromadb`. Use persistent mode so the database survives between runs.

Write two scripts:

**`ingest.py`** — reads all files from `data/embeddings/` and upserts all chunks into a ChromaDB collection.

- Collection name: `cuny_rag`
- Use `chunk_id` as the document ID
- Metadata to store per chunk: `college`, `category`, `source`, `title`, `section`, `scraped_date`
- Should be idempotent: running it twice shouldn't create duplicates
- Add `data/chromadb/` to `.gitignore` — the database does not go in the repo

**`retriever.py`** — a clean retrieval interface. This is what the rest of the team will import.

Implement a `retrieve()` function with this signature:

```python
def retrieve(query: str, n_results: int = 5, filters: dict = None) -> list[dict]:
    """
    Embed the query and return the top n_results chunks from ChromaDB.

    filters: optional metadata filter, e.g.
        {"college": "Baruch College"}
        {"category": "financial_aid"}

    Returns a list of dicts, each with:
        - text
        - source
        - title
        - college
        - category
        - score (distance)
    """
```

Also include a `__main__` block so the script can be tested directly:
```
python retriever.py "How do I apply for financial aid at Baruch?"
```

### Definition of Done

- `ingest.py` populates ChromaDB without errors
- `retriever.py` returns sensible results for a test query
- `retrieve()` is documented and the interface is posted in the group chat
- `data/chromadb/` is in `.gitignore`

### Push

```
git add ingest.py retriever.py .gitignore
git commit -m "add chromadb ingestion and retrieval interface"
git push
```

---

## Workstream 4 — Evaluation Prep (Monda)

### What you're doing

Two things: finishing the eval question set, and writing a retrieval evaluation script.

### Part 1 — Finish the question set

25–30 questions in the Google Sheet by Saturday. Good coverage across colleges and categories. Use the notes column to flag anything ambiguous or college-specific. If you need questions for categories you didn't scrape, skim those pages briefly — you don't need to scrape them, just enough to write realistic questions.

### Part 2 — Retrieval evaluation script

Write `eval_retrieval.py`. This script will:

1. Load questions from the Google Sheet (export as CSV for now)
2. For each question, call `retriever.retrieve(question, n_results=5)`
3. For each result, print the question, expected answer, and top retrieved chunk so a human can judge relevance

You can't run the full script until Sai's retriever is ready — but write the structure, CSV loading, and output formatting now, and stub out the retrieve call in the meantime.

### Definition of Done

- Google Sheet has 25–30 questions with expected answers, categories, colleges, and notes
- `eval_retrieval.py` exists and is structured correctly (retrieve call can be stubbed)

### Push

```
git add eval_retrieval.py
git commit -m "add retrieval eval script"
git push
```

---

## Notes for Everyone

**Dependency order:** chunking → embedding → ingestion → retrieval. Communicate early if you're blocked — post in the group chat, don't wait until Saturday.

**Metadata consistency:** `college` and `category` must match the controlled vocabulary exactly at every stage. These fields are used for filtering — a typo means that chunk is invisible to filtered queries.

**`requirements.txt`:** if you add a new dependency, add it before you push. New ones this week: `tiktoken`, `sentence-transformers`, `chromadb`.

**Definition of Done:**
- `chunker.py` runs cleanly over all of `data/raw/`
- `embedder.py` runs cleanly over all of `data/chunks/`
- `ingest.py` populates ChromaDB without errors
- `retriever.py` returns sensible results for a test query
- Eval question set is complete (25–30 questions)
- All scripts committed and pushed
