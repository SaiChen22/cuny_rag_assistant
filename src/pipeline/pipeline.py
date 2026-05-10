from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from chunker import (
    RAW_DIR,
    CHUNKS_DIR,
    chunk_documents,
    load_documents,
    normalize_documents,
    process_file,
    save_documents,
)
from embedder import (
    EMBEDDINGS_DIR,
    MODEL_NAME,
    _iter_chunk_files,
    _read_chunks,
)
from ingest import (
    CHROMA_DIR,
    COLLECTION_NAME,
    ingest,
)

from sentence_transformers import SentenceTransformer


class DataPipeline:
    """
    Unified data pipeline for:
    1. Chunking raw documents
    2. Generating embeddings
    3. Ingesting into ChromaDB
    """

    def __init__(
        self,
        raw_dir: Path = RAW_DIR,
        chunks_dir: Path = CHUNKS_DIR,
        embeddings_dir: Path = EMBEDDINGS_DIR,
        chroma_dir: Path = CHROMA_DIR,
        collection_name: str = COLLECTION_NAME,
        model_name: str = MODEL_NAME,
        reset_chunks: bool = True,
        reset_embeddings: bool = True,
    ):
        self.raw_dir = Path(raw_dir)
        self.chunks_dir = Path(chunks_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.chroma_dir = Path(chroma_dir)
        self.collection_name = collection_name
        self.model_name = model_name
        self.reset_chunks = reset_chunks
        self.reset_embeddings = reset_embeddings

        self.model: SentenceTransformer | None = None
        self.total_documents = 0
        self.total_chunks = 0
        self.total_embeddings = 0
        self.total_ingested = 0

    def log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp and level."""
        print(f"[{level}] {message}")

    def step_1_chunk_documents(self) -> bool:
        """Step 1: Chunk raw documents."""
        self.log("=" * 60)
        self.log("STEP 1: Chunking documents", "INFO")
        self.log("=" * 60)

        if not self.raw_dir.exists():
            self.log(f"Raw data directory not found: {self.raw_dir}", "ERROR")
            return False

        if self.reset_chunks and self.chunks_dir.exists():
            self.log(f"Removing existing chunks directory: {self.chunks_dir}", "INFO")
            shutil.rmtree(self.chunks_dir)

        raw_files = sorted(
            path for path in self.raw_dir.rglob("*.json") if path.is_file()
        )

        if not raw_files:
            self.log(f"No raw JSON files found under {self.raw_dir}", "WARNING")
            return False

        self.log(f"Found {len(raw_files)} raw files to process", "INFO")

        for idx, input_file in enumerate(raw_files, 1):
            self.log(f"[{idx}/{len(raw_files)}] Processing: {input_file.name}", "INFO")

            try:
                payload = load_documents(input_file)
                documents = normalize_documents(payload)

                if not documents:
                    self.log(f"  No documents found in {input_file.name}", "WARNING")
                    continue

                relative_path = input_file.relative_to(self.raw_dir)
                output_file = self.chunks_dir / relative_path
                source_filename = input_file.stem

                chunked_docs = chunk_documents(
                    documents, source_filename=source_filename
                )
                save_documents(chunked_docs, output_file)
                self.total_documents += len(documents)
                self.total_chunks += len(chunked_docs)

            except Exception as e:
                self.log(f"  Error processing {input_file}: {e}", "ERROR")
                continue

        self.log(
            f"Step 1 complete: {self.total_documents} documents → {self.total_chunks} chunks",
            "INFO",
        )
        return True

    def step_2_embed_chunks(self) -> bool:
        """Step 2: Generate embeddings for chunks."""
        self.log("")
        self.log("=" * 60)
        self.log("STEP 2: Generating embeddings", "INFO")
        self.log("=" * 60)

        if not self.chunks_dir.exists():
            self.log(f"Chunks directory not found: {self.chunks_dir}", "ERROR")
            return False

        if self.reset_embeddings and self.embeddings_dir.exists():
            self.log(f"Removing existing embeddings directory: {self.embeddings_dir}", "INFO")
            shutil.rmtree(self.embeddings_dir)

        self.log(f"Loading embedding model: {self.model_name}", "INFO")
        try:
            self.model = SentenceTransformer(self.model_name, device="cpu")
        except Exception as e:
            self.log(f"Error loading model {self.model_name}: {e}", "ERROR")
            return False

        files = _iter_chunk_files(self.chunks_dir)

        if not files:
            self.log(f"No chunk files found in {self.chunks_dir}", "WARNING")
            return False

        self.log(f"Found {len(files)} chunk files to embed", "INFO")

        for idx, file_path in enumerate(files, 1):
            self.log(f"[{idx}/{len(files)}] Embedding: {file_path.name}", "INFO")

            try:
                chunks = _read_chunks(file_path)
                valid_chunks = []

                for chunk in chunks:
                    text = chunk.get("text", "")
                    if isinstance(text, str) and text.strip():
                        valid_chunks.append(chunk)
                    else:
                        self.log(
                            f"  Skipping chunk with missing/empty text in {file_path.name}",
                            "WARNING",
                        )

                if not valid_chunks:
                    self.log(
                        f"  No valid chunks found in {file_path.name}",
                        "WARNING",
                    )
                    continue

                texts = [chunk["text"] for chunk in valid_chunks]
                embeddings = self.model.encode(texts).tolist()

                for chunk, embedding in zip(valid_chunks, embeddings):
                    chunk["embedding"] = embedding

                output_path = self.embeddings_dir / file_path.name
                output_path.parent.mkdir(parents=True, exist_ok=True)

                import json

                with output_path.open("w", encoding="utf-8") as f:
                    json.dump(valid_chunks, f, indent=2)

                self.log(
                    f"  Embedded {len(valid_chunks)} chunks from {file_path.name}",
                    "INFO",
                )
                self.total_embeddings += len(valid_chunks)

            except Exception as e:
                self.log(f"  Error processing {file_path}: {e}", "ERROR")
                continue

        self.log(f"Step 2 complete: {self.total_embeddings} chunks embedded", "INFO")
        return True

    def step_3_ingest_to_chromadb(self) -> bool:
        """Step 3: Ingest embedded chunks into ChromaDB."""
        self.log("")
        self.log("=" * 60)
        self.log("STEP 3: Ingesting into ChromaDB", "INFO")
        self.log("=" * 60)

        if not self.embeddings_dir.exists():
            self.log(f"Embeddings directory not found: {self.embeddings_dir}", "ERROR")
            return False

        try:
            self.total_ingested = ingest(
                embeddings_dir=self.embeddings_dir,
                chroma_dir=self.chroma_dir,
                collection_name=self.collection_name,
            )
        except Exception as e:
            self.log(f"Error during ingestion: {e}", "ERROR")
            return False

        self.log(
            f"Step 3 complete: {self.total_ingested} chunks ingested into ChromaDB",
            "INFO",
        )
        return True

    def run(self) -> bool:
        """Run the complete pipeline."""
        self.log("")
        self.log("🚀 CUNY RAG Assistant - Data Pipeline")
        self.log("=" * 60)

        start_time = time.time()

        # Step 1: Chunk
        if not self.step_1_chunk_documents():
            if self.total_chunks == 0:
                self.log("Pipeline aborted: chunking failed", "ERROR")
                return False

        # Step 2: Embed
        if not self.step_2_embed_chunks():
            if self.total_embeddings == 0:
                self.log("Pipeline aborted: embedding failed", "ERROR")
                return False

        # Step 3: Ingest
        if not self.step_3_ingest_to_chromadb():
            self.log("Pipeline aborted: ingestion failed", "ERROR")
            return False

        # Summary
        elapsed_time = time.time() - start_time
        self.log("")
        self.log("=" * 60)
        self.log("✅ PIPELINE COMPLETED SUCCESSFULLY", "INFO")
        self.log("=" * 60)
        self.log(f"Total documents processed:  {self.total_documents}", "INFO")
        self.log(f"Total chunks created:       {self.total_chunks}", "INFO")
        self.log(f"Total chunks embedded:      {self.total_embeddings}", "INFO")
        self.log(f"Total chunks ingested:      {self.total_ingested}", "INFO")
        self.log(f"Time elapsed:               {elapsed_time:.2f}s", "INFO")
        self.log("=" * 60)

        return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CUNY RAG Assistant - Unified Data Pipeline"
    )
    parser.add_argument(
        "--raw-dir", default=str(RAW_DIR), help="Path to raw data directory"
    )
    parser.add_argument(
        "--chunks-dir", default=str(CHUNKS_DIR), help="Path to chunks output directory"
    )
    parser.add_argument(
        "--embeddings-dir",
        default=str(EMBEDDINGS_DIR),
        help="Path to embeddings output directory",
    )
    parser.add_argument(
        "--chroma-dir",
        default=str(CHROMA_DIR),
        help="Path to ChromaDB directory",
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help="ChromaDB collection name",
    )
    parser.add_argument(
        "--model",
        default=MODEL_NAME,
        help="Sentence transformer model name",
    )
    parser.add_argument(
        "--keep-chunks",
        action="store_true",
        help="Keep existing chunks (don't reset)",
    )
    parser.add_argument(
        "--keep-embeddings",
        action="store_true",
        help="Keep existing embeddings (don't reset)",
    )

    args = parser.parse_args()

    pipeline = DataPipeline(
        raw_dir=args.raw_dir,
        chunks_dir=args.chunks_dir,
        embeddings_dir=args.embeddings_dir,
        chroma_dir=args.chroma_dir,
        collection_name=args.collection,
        model_name=args.model,
        reset_chunks=not args.keep_chunks,
        reset_embeddings=not args.keep_embeddings,
    )

    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
