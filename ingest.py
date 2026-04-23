from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import chromadb


EMBEDDINGS_DIR = Path("data/embeddings")
CHROMA_DIR = Path("data/chromadb")
COLLECTION_NAME = "cuny_rag"
BATCH_SIZE = 256

BASE_METADATA_FIELDS = ["college", "category", "source", "title", "section", "scraped_date"]


def _iter_embedding_files(embeddings_dir: Path) -> list[Path]:
    return sorted(p for p in embeddings_dir.rglob("*.json") if p.is_file())


def _read_chunks(file_path: Path) -> list[dict[str, Any]]:
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            return [item for item in chunks if isinstance(item, dict)]

    raise ValueError(f"Unsupported embedding JSON format: {file_path}")


def _chunk_to_chroma_item(chunk: dict[str, Any], file_path: Path) -> tuple[str, str, list[float], dict[str, Any]]:
    chunk_id = chunk.get("chunk_id")
    text = chunk.get("text")
    embedding = chunk.get("embedding")

    if not isinstance(chunk_id, str) or not chunk_id.strip():
        raise ValueError(f"Missing or invalid chunk_id in {file_path}")
    if not isinstance(text, str):
        raise ValueError(f"Missing or invalid text for chunk_id={chunk_id} in {file_path}")
    if not isinstance(embedding, list) or not embedding:
        raise ValueError(f"Missing or invalid embedding for chunk_id={chunk_id} in {file_path}")

    metadata: dict[str, Any] = {}
    for key in BASE_METADATA_FIELDS:
        value = chunk.get(key)
        if value is not None:
            metadata[key] = value

    return chunk_id, text, embedding, metadata


def ingest(
    embeddings_dir: Path = EMBEDDINGS_DIR,
    chroma_dir: Path = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    if not embeddings_dir.exists():
        raise FileNotFoundError(f"Embeddings directory not found: {embeddings_dir}")

    chroma_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name=collection_name)

    files = _iter_embedding_files(embeddings_dir)
    if not files:
        print(f"No embedding files found under {embeddings_dir}")
        return 0

    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, Any]] = []
    total = 0

    def flush() -> None:
        nonlocal ids, documents, embeddings, metadatas
        if not ids:
            return
        collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        ids, documents, embeddings, metadatas = [], [], [], []

    for file_path in files:
        chunks = _read_chunks(file_path)
        for chunk in chunks:
            chunk_id, text, embedding, metadata = _chunk_to_chroma_item(chunk, file_path)
            ids.append(chunk_id)
            documents.append(text)
            embeddings.append(embedding)
            metadatas.append(metadata)
            total += 1

            if len(ids) >= BATCH_SIZE:
                flush()

    flush()
    print(f"Ingested/upserted {total} chunks into '{collection_name}'")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest embedded chunks into ChromaDB.")
    parser.add_argument("--embeddings-dir", default=str(EMBEDDINGS_DIR))
    parser.add_argument("--chroma-dir", default=str(CHROMA_DIR))
    parser.add_argument("--collection", default=COLLECTION_NAME)
    args = parser.parse_args()

    ingest(
        embeddings_dir=Path(args.embeddings_dir),
        chroma_dir=Path(args.chroma_dir),
        collection_name=args.collection,

    )


if __name__ == "__main__":
    main()