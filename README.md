# CUNY RAG Assistant

A retrieval-augmented generation (RAG) system that answers CUNY student questions using scraped policy and services data. A React frontend talks to a FastAPI backend; the backend runs **hybrid retrieval** (dense vector search + BM25, merged with Reciprocal Rank Fusion) and sends the top chunks to an OpenAI model for a citation-aware answer.

## Architecture

```
data/raw/*.json  →  chunker  →  data/chunks/
                                      ↓
                               embedder  →  data/embeddings/
                                                  ↓
                                            ingest  →  data/chromadb/
                                                              ↑
User → React (Vite :5173) → FastAPI (:8000) → retriever (Dense + BM25 + RRF)
                                  ↓
                             OpenAI API  →  citation answer
```

See [`arch/cuny-rag-assistant.architecture.html`](arch/cuny-rag-assistant.architecture.html) for an interactive diagram (open locally in a browser).

## Data coverage

Ten scraped categories across multiple CUNY colleges:

| Category | Notes |
|---|---|
| `academic_policies` | Baruch, Brooklyn, City Tech, CSI, John Jay, Lehman, Medgar Evers, Queens, York |
| `admissions` | Freshman, transfer, graduate, college-specific |
| `advising` | Baruch, Brooklyn, Hunter, Lehman, Medgar Evers, Staten Island, York |
| `campus_resources` | Baruch, Brooklyn, City Tech, CSI, Hunter, John Jay, Lehman, Queens, York |
| `degree_requirements` | CUNY-wide |
| `financial_aid` | FAFSA, grants, loans, scholarships, SAP, state aid, work-study |
| `graduation` | CUNY-wide |
| `registration_enrollment` | Baruch, Brooklyn, Hunter |
| `transfer` | CUNY-wide |
| `tuition_and_fees` | Billing, bursar, deadlines, payment, refunds, tax, waivers |

## Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key (only required for `/api/ask`; retrieval-only paths work without it)

## Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd cuny-rag-assistant

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create the .env file at the repo root
cat > .env <<'EOF'
OPENAI_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EOF
```

| Variable | Default | Description |
|---|---|---|
| `OPENAI_KEY` / `OPENAI_API_KEY` | — | Required for answer generation |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers model (384-dim) |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` or `cuda`; CPU is the safe default |

## Build the vector store

Run once (or whenever `data/raw/` changes). All commands must be run from the **repo root**.

```bash
# Full rebuild — chunks, embeddings, ChromaDB
python src/pipeline/pipeline.py

# Re-embed and re-ingest but keep existing chunks
python src/pipeline/pipeline.py --keep-chunks

# Keep both chunks and embeddings, only re-ingest
python src/pipeline/pipeline.py --keep-chunks --keep-embeddings
```

The pipeline takes ~5–10 min on CPU for the full corpus. See `PIPELINE.md` for detailed options.

## Run

Start the backend and frontend in separate terminals from the repo root:

```bash
# Terminal 1 — API server (warms embedding model + BM25 index on startup)
./.venv/bin/python backend/serve.py

# Terminal 2 — frontend dev server
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** in your browser.

## API reference

### `GET /api/health`

Returns `{"ok": true}` when the server is up.

### `POST /api/ask`

```json
{
  "query": "How do I apply for financial aid at Baruch?",
  "n_results": 5,
  "filters": { "college": "Baruch College", "category": "financial_aid" }
}
```

`filters` is optional. Supported filter keys: `college`, `category`.

Response:

```json
{
  "answer": "To apply for financial aid at Baruch... [1][2]",
  "sources": [
    { "index": 1, "title": "...", "college": "Baruch College", "category": "financial_aid", "source": "https://..." }
  ],
  "model": "gpt-4o-mini"
}
```

## CLI tools

```bash
# One-shot question (prints answer to stdout)
python backend/ask.py "What are the transfer requirements at Queens College?"

# Direct retrieval — no LLM, shows top chunks
python src/pipeline/retriever.py "graduation requirements" --college "Brooklyn College" --n-results 3
```

## Project layout

```
backend/
  serve.py          FastAPI app + CORS config
  ask.py            CLI wrapper for one-shot questions
src/pipeline/
  chunker.py        tiktoken chunking (400-tok / 50-tok overlap)
  embedder.py       Sentence-Transformers batch embedding
  ingest.py         ChromaDB upsert (batches of 256)
  retriever.py      Hybrid dense + BM25 + RRF retrieval
  generator.py      OpenAI prompt assembly and answer generation
  pipeline.py       Orchestrates chunker → embedder → ingest
frontend/src/
  App.jsx           React chat UI
data/raw/           Scraped CUNY JSON (committed)
data/chunks/        Generated — gitignored, rebuild via pipeline
data/embeddings/    Generated — gitignored, rebuild via pipeline
data/chromadb/      Generated — gitignored, rebuild via pipeline
arch/               Architecture diagram (JSON spec + rendered HTML)
```
