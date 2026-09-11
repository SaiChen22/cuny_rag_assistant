from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


CHROMA_DIR = Path("data/chromadb")
COLLECTION_NAME = "cuny_rag"
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEFAULT_EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

# Module-level cache: built once on first retrieve() call, reused thereafter.
_bm25_index: BM25Okapi | None = None
_bm25_corpus: list[dict[str, Any]] | None = None  # [{id, text, metadata}, ...]
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    """Return the SentenceTransformer, loading it once on first call."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            DEFAULT_EMBEDDING_MODEL, device=DEFAULT_EMBEDDING_DEVICE
        )
    return _embedding_model


def warmup() -> None:
    """Pre-load embedding model and BM25 index so the first retrieve() is fast.

    Safe to call multiple times — both helpers are idempotent.
    """
    _get_embedding_model()
    _ = _get_bm25_index()


def _get_collection(chroma_dir: Path = CHROMA_DIR, collection_name: str = COLLECTION_NAME):
    if not chroma_dir.exists():
        raise FileNotFoundError(
            f"Chroma directory not found at {chroma_dir}. Run ingest.py first."
        )
    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_or_create_collection(name=collection_name)


def _load_corpus() -> list[dict[str, Any]]:
    """Fetch every document from ChromaDB and return as a flat list."""
    collection = _get_collection()
    result = collection.get(include=["documents", "metadatas"])
    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    return [
        {"id": doc_id, "text": text, "metadata": dict(meta) if meta else {}}
        for doc_id, text, meta in zip(ids, documents, metadatas)
    ]


def _get_bm25_index() -> tuple[BM25Okapi, list[dict[str, Any]]]:
    """Return (BM25Okapi index, corpus), building and caching on first call."""
    global _bm25_index, _bm25_corpus
    if _bm25_index is None:
        _bm25_corpus = _load_corpus()
        tokenized = [doc["text"].lower().split() for doc in _bm25_corpus]
        _bm25_index = BM25Okapi(tokenized)
    assert _bm25_corpus is not None
    return _bm25_index, _bm25_corpus


def _bm25_search(query: str, n: int, filters: dict[str, Any] | None) -> list[str]:
    """Return top-n doc IDs ranked by BM25 score, with optional metadata filtering."""
    index, corpus = _get_bm25_index()
    scores = index.get_scores(query.lower().split())
    ranked = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    if filters:
        ranked = [
            i for i in ranked
            if all(corpus[i]["metadata"].get(k) == v for k, v in filters.items())
        ]
    return [corpus[ranked[i]]["id"] for i in range(min(n, len(ranked)))]


def _build_where_clause(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert plain metadata filters into a ChromaDB where clause."""
    if not filters:
        return None
    if len(filters) == 1:
        key, value = next(iter(filters.items()))
        return {key: value}
    return {"$and": [{key: value} for key, value in filters.items()]}


def _reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    """
    Merge multiple ranked lists of doc IDs using Reciprocal Rank Fusion.

    Formula: score(d) = Σ  1 / (rank_of_d_in_list + k)
                       lists

    Args:
        ranked_lists: e.g. [dense_ids, bm25_ids], each ordered best-first.
        k: smoothing constant (default 60 per the original RRF paper).

    Returns:
        Doc IDs sorted by descending RRF score.

    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, doc_id in enumerate(ranked_list):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rank + k)
    return sorted(scores, key=lambda x: scores[x], reverse=True)



def retrieve(query: str, n_results: int = 5, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Hybrid retrieval: dense vector search + BM25 keyword search, merged with RRF.

    filters: optional metadata filter, e.g.
        {"college": "Baruch College"}
        {"category": "financial_aid"}

    Returns a list of dicts, each with:
        - text
        - source
        - title
        - college
        - category
        - score  (0-indexed RRF rank; 0 = best match)
    """
    fetch_k = n_results * 4  # wider candidate pool so RRF has enough to merge

    # --- Dense search: embed query, retrieve top fetch_k doc IDs from ChromaDB ---
    collection = _get_collection()
    # Default to CPU to avoid CUDA runtime failures on older or unsupported GPUs.
    # Cached at module level so the model is loaded only once across requests.
    model = _get_embedding_model()
    query_embedding = model.encode(query).tolist()

    dense_kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": fetch_k,
        "include": ["documents", "metadatas"],
    }
    where_clause = _build_where_clause(filters)
    if where_clause:
        dense_kwargs["where"] = where_clause

    dense_result = collection.query(**dense_kwargs)
    dense_ids: list[str] = (dense_result.get("ids") or [[]])[0]

    # --- BM25 search ---
    bm25_ids = _bm25_search(query, fetch_k, filters)

    # --- RRF merge ---
    merged_ids = _reciprocal_rank_fusion([dense_ids, bm25_ids])

    # --- Build result rows from in-memory corpus (avoids a second DB round-trip) ---
    _, corpus = _get_bm25_index()
    corpus_by_id = {doc["id"]: doc for doc in corpus}

    rows: list[dict[str, Any]] = []
    for rank, doc_id in enumerate(merged_ids[:n_results]):
        entry = corpus_by_id.get(doc_id)
        if entry is None:
            continue
        meta: dict[str, Any] = entry["metadata"]
        rows.append(
            {
                "text": entry["text"],
                "source": meta.get("source"),
                "title": meta.get("title"),
                "college": meta.get("college"),
                "category": meta.get("category"),
                "score": rank,
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Query CUNY RAG chunks from ChromaDB.")
    parser.add_argument("query", type=str, help="Natural-language query text")
    parser.add_argument("--n-results", type=int, default=5)
    parser.add_argument("--college", type=str, default=None)
    parser.add_argument("--category", type=str, default=None)
    args = parser.parse_args()

    filters: dict[str, Any] = {}
    if args.college:
        filters["college"] = args.college
    if args.category:
        filters["category"] = args.category

    records = retrieve(
        query=args.query,
        n_results=args.n_results,
        filters=filters or None,
    )

    if not records:
        print("No results found.")
        return

    for idx, record in enumerate(records, start=1):
        print(f"\n[{idx}] score={record['score']}")
        print(f"title: {record['title']}")
        print(f"college: {record['college']}")
        print(f"category: {record['category']}")
        print(f"source: {record['source']}")
        print(f"text: {record['text']}")


if __name__ == "__main__":
    main()