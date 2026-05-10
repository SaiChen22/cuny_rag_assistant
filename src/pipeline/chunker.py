from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import tiktoken


RAW_DIR = Path("data/raw")
CHUNKS_DIR = Path("data/chunks")
CHUNK_SIZE = 400
OVERLAP = 50
CHUNK_ID_WIDTH = 3

enc = tiktoken.get_encoding("cl100k_base")


def load_documents(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_documents(documents: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(documents, file_handle, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(documents)} documents to {output_path}")


def normalize_documents(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [doc for doc in payload if isinstance(doc, dict)]

    if isinstance(payload, dict):
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            return [doc for doc in chunks if isinstance(doc, dict)]

    return []


def chunk_text_tokens(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    if not isinstance(text, str):
        text = ""

    tokens = enc.encode(text)
    if not tokens:
        return [""]

    if len(tokens) <= chunk_size:
        return [text]

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end >= len(tokens):
            break
        start += step

    return chunks


def build_chunk_record(doc: dict[str, Any], chunk_text: str, chunk_index: int, total_chunks: int, source_filename: str, doc_index: int) -> dict[str, Any]:
    return {
        "chunk_id": f"{source_filename}_{doc_index}_chunk_{chunk_index:0{CHUNK_ID_WIDTH}d}",
        "text": chunk_text,
        "source": doc.get("source", ""),
        "title": doc.get("title", ""),
        "college": doc.get("college", ""),
        "category": doc.get("category", ""),
        "section": doc.get("section", ""),
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "scraped_date": doc.get("scraped_date", ""),
    }


def chunk_documents(documents: list[dict[str, Any]], source_filename: str, doc_index_offset: int = 0) -> list[dict[str, Any]]:
    chunked_docs: list[dict[str, Any]] = []

    for local_doc_index, doc in enumerate(documents, start=doc_index_offset):
        text = doc.get("text", "")
        chunks = chunk_text_tokens(text)
        total_chunks = len(chunks)

        for chunk_index, chunk_text in enumerate(chunks):
            chunked_docs.append(
                build_chunk_record(
                    doc=doc,
                    chunk_text=chunk_text,
                    chunk_index=chunk_index,
                    total_chunks=total_chunks,
                    source_filename=source_filename,
                    doc_index=local_doc_index,
                )
            )

    return chunked_docs


def process_file(input_file: Path) -> None:
    try:
        payload = load_documents(input_file)
    except Exception as exc:
        print(f"Error loading {input_file}: {exc}")
        return

    documents = normalize_documents(payload)
    if not documents:
        print(f"No documents found in {input_file}")
        return

    relative_path = input_file.relative_to(RAW_DIR)
    output_file = CHUNKS_DIR / relative_path
    source_filename = input_file.stem

    chunked_docs = chunk_documents(documents, source_filename=source_filename)
    save_documents(chunked_docs, output_file)


def main() -> None:
    if not RAW_DIR.exists():
        print(f"Raw data directory not found: {RAW_DIR}")
        return

    if CHUNKS_DIR.exists():
        shutil.rmtree(CHUNKS_DIR)

    raw_files = sorted(path for path in RAW_DIR.rglob("*.json") if path.is_file())
    if not raw_files:
        print(f"No raw JSON files found under {RAW_DIR}")
        return

    for input_file in raw_files:
        process_file(input_file)


if __name__ == "__main__":
    main()