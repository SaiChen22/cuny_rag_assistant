from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer


CHUNKS_DIR = Path("data/chunks")
EMBEDDINGS_DIR = Path("data/embeddings")
MODEL_NAME = "all-MiniLM-L6-v2"


def _iter_chunk_files(chunks_dir: Path) -> list[Path]:
    return sorted(p for p in chunks_dir.rglob("*.json") if p.is_file())


def _read_chunks(file_path: Path) -> list[dict[str, Any]]:
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            return [item for item in chunks if isinstance(item, dict)]

    raise ValueError(f"Unsupported chunk JSON format: {file_path}")


def embed_chunks() -> int:
    if not CHUNKS_DIR.exists():
        print("No data/chunks directory found.")
        return 0

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    files = _iter_chunk_files(CHUNKS_DIR)
    if not files:
        print("No chunk files found.")
        return 0

    total = 0

    for file_path in files:
        chunks = _read_chunks(file_path)

        valid_chunks = []

        for chunk in chunks:
            text = chunk.get("text", "")
            if isinstance(text, str) and text.strip():
                valid_chunks.append(chunk)
            else:
                print(f"Skipping chunk with missing/empty text in {file_path}")

        if not valid_chunks:
            print(f"No valid chunks found in {file_path}")
            continue

        texts = [chunk["text"] for chunk in valid_chunks]

        embeddings = model.encode(texts).tolist()

        for chunk, embedding in zip(valid_chunks, embeddings):
            chunk["embedding"] = embedding

        output_path = EMBEDDINGS_DIR / file_path.name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(valid_chunks, f, indent=2)

        print(f"Embedded {len(valid_chunks)} chunks from {file_path}")
        total += len(valid_chunks)

    print(f"Finished embedding {total} chunks.")
    return total


if __name__ == "__main__":
    embed_chunks()