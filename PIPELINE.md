# Data Pipeline Documentation

## Overview

The `pipeline.py` module provides a unified data pipeline that orchestrates three sequential steps:

1. **Step 1: Chunking** - Chunks raw documents into tokens with configurable size and overlap
2. **Step 2: Embedding** - Generates embeddings for all chunks using Sentence Transformers
3. **Step 3: Ingestion** - Stores embeddings and metadata into ChromaDB vector database

## Quick Start

### Basic Usage

Run the pipeline with default settings:

```bash
cd src/pipeline
python pipeline.py
```

### With Custom Directories

```bash
python pipeline.py \
  --raw-dir data/raw \
  --chunks-dir data/chunks \
  --embeddings-dir data/embeddings \
  --chroma-dir data/chromadb
```

### Preserve Existing Data

By default, the pipeline resets chunks and embeddings directories. To keep existing data:

```bash
python pipeline.py --keep-chunks --keep-embeddings
```

## Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--raw-dir` | `data/raw` | Path to raw documents directory |
| `--chunks-dir` | `data/chunks` | Output directory for chunked documents |
| `--embeddings-dir` | `data/embeddings` | Output directory for embeddings |
| `--chroma-dir` | `data/chromadb` | ChromaDB database directory |
| `--collection` | `cuny_rag` | ChromaDB collection name |
| `--model` | `all-MiniLM-L6-v2` | Sentence Transformer model |
| `--keep-chunks` | `False` | Don't reset chunks directory |
| `--keep-embeddings` | `False` | Don't reset embeddings directory |

## Pipeline Stages

### Stage 1: Chunking

- **Input**: Raw JSON documents from `data/raw/`
- **Processing**:
  - Normalizes document format
  - Chunks text into 400-token segments with 50-token overlap
  - Preserves metadata (title, college, category, section, etc.)
- **Output**: JSON files in `data/chunks/` with chunk records containing:
  - `chunk_id`: Unique identifier
  - `text`: Chunk content
  - `source`: Source URL/reference
  - `title`: Document title
  - `college`: College name
  - `category`: Content category
  - `section`: Section within document
  - `chunk_index`: Position in document
  - `total_chunks`: Number of chunks for document
  - `scraped_date`: When document was scraped

### Stage 2: Embedding

- **Input**: Chunked documents from `data/chunks/`
- **Model**: `all-MiniLM-L6-v2` (384-dimensional embeddings)
- **Processing**:
  - Loads SentenceTransformer model
  - Generates embeddings for each chunk
  - Validates chunk text quality
  - Skips chunks with empty or missing text
- **Output**: JSON files in `data/embeddings/` with chunks + embeddings

### Stage 3: Ingestion

- **Input**: Embedded chunks from `data/embeddings/`
- **Database**: ChromaDB (persistent storage in `data/chromadb/`)
- **Processing**:
  - Validates embeddings and metadata
  - Upserts chunks in batches of 256
  - Creates/updates ChromaDB collection
  - Extracts metadata fields for filtering
- **Output**: Vector database collection `cuny_rag` with:
  - Chunk IDs
  - Text documents
  - Vector embeddings
  - Searchable metadata

## Example Output

```
[INFO] 🚀 CUNY RAG Assistant - Data Pipeline
============================================================
[INFO] ============================================================
[INFO] STEP 1: Chunking documents
[INFO] ============================================================
[INFO] Found 15 raw files to process
[INFO] [1/15] Processing: academic_policies.json
[INFO] Step 1 complete: 245 documents → 1,823 chunks

[INFO] ============================================================
[INFO] STEP 2: Generating embeddings
[INFO] ============================================================
[INFO] Loading embedding model: all-MiniLM-L6-v2
[INFO] Found 10 chunk files to embed
[INFO] [1/10] Embedding: academic_policies.json
[INFO] Step 2 complete: 1,823 chunks embedded

[INFO] ============================================================
[INFO] STEP 3: Ingesting into ChromaDB
[INFO] ============================================================
[INFO] Ingested/upserted 1,823 chunks into 'cuny_rag' (0 skipped)

[INFO] ✅ PIPELINE COMPLETED SUCCESSFULLY
============================================================
[INFO] Total documents processed:  245
[INFO] Total chunks created:       1,823
[INFO] Total chunks embedded:      1,823
[INFO] Total chunks ingested:      1,823
[INFO] Time elapsed:               342.45s
============================================================
```

## Architecture

```
Raw Documents (data/raw/)
        ↓
   Chunker
        ↓
   Chunks (data/chunks/)
        ↓
   Embedder
        ↓
   Embeddings (data/embeddings/)
        ↓
   Ingester
        ↓
   ChromaDB (data/chromadb/)
```

## Error Handling

The pipeline includes robust error handling:

- **Graceful degradation**: Continues processing if individual files fail
- **Validation**: Checks for required fields at each stage
- **Logging**: Detailed INFO, WARNING, and ERROR messages
- **Exit codes**: Returns 0 on success, 1 on failure

## Performance Notes

- **Chunking**: ~5-10 seconds per 100 documents
- **Embedding**: ~1-2 minutes per 1,000 chunks (on CPU)
- **Ingestion**: ~30-60 seconds per 1,000 chunks

To speed up embedding, the model can be moved to GPU by modifying the device parameter.

## Integration with Existing Modules

The pipeline integrates the following existing modules:

- `chunker.py`: Document normalization and chunking logic
- `embedder.py`: Embedding generation using SentenceTransformer
- `ingest.py`: ChromaDB ingestion and upsert

These modules can still be used independently, but the unified pipeline is recommended for standard workflows.
