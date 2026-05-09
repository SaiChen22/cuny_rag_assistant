"""FastAPI service exposing the CUNY RAG generator over HTTP.

Run as a background process:
    ./.venv/bin/python serve.py &
or with logging captured:
    nohup ./.venv/bin/python serve.py >serve.log 2>&1 &

The lifespan startup hook pre-loads the embedding model and BM25 index so the
first request hits warm caches.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Run with this file's directory as cwd so retriever.py's relative paths
# (data/chromadb, data/embeddings) resolve correctly regardless of launch dir.
_PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(_PROJECT_ROOT)

# Make src/pipeline modules importable.
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "pipeline"))

import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from generator import generate_answer  # noqa: E402
from retriever import warmup  # noqa: E402

logger = logging.getLogger("cuny_rag.serve")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("warming retriever (loading embedding model + BM25 index)...")
    warmup()
    logger.info("retriever ready")
    yield


app = FastAPI(title="CUNY RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    query: str
    n_results: int = 5
    filters: dict[str, Any] | None = None


class Source(BaseModel):
    index: int
    title: str | None = None
    college: str | None = None
    category: str | None = None
    source: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict[str, Any]:
    try:
        return generate_answer(
            query=request.query,
            n_results=request.n_results,
            filters=request.filters,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    uvicorn.run("serve:app", host="127.0.0.1", port=8000, reload=False)
