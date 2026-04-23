from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_DIR = Path("data/chromadb")
COLLECTION_NAME = "cuny_rag"
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


def _get_collection(chroma_dir: Path = CHROMA_DIR, collection_name: str = COLLECTION_NAME):
    if not chroma_dir.exists():
        raise FileNotFoundError(
            f"Chroma directory not found at {chroma_dir}. Run ingest.py first."
        )
    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_or_create_collection(name=collection_name)



def retrieve(query: str, n_results: int = 5, filters: dict | None = None) -> list[dict]:
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
    collection = _get_collection()
    
    model = SentenceTransformer(DEFAULT_EMBEDDING_MODEL)
    query_embedding = model.encode(query).tolist()

    query_kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if filters:
        query_kwargs["where"] = filters

    result = collection.query(**query_kwargs)

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    rows: list[dict] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        safe_meta = meta or {}
        rows.append(
            {
                "text": doc,
                "source": safe_meta.get("source"),
                "title": safe_meta.get("title"),
                "college": safe_meta.get("college"),
                "category": safe_meta.get("category"),
                "score": distance,
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