from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# Allow `from retriever import retrieve` whether run as a script or imported.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from retriever import retrieve  # noqa: E402

# Load .env from repo root so OPENAI_KEY etc. are available without shell export.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


SYSTEM_PROMPT = (
    "You are an assistant for City University of New York (CUNY) information. "
    "Answer the user's question using ONLY the numbered sources in the user message.\n\n"
    "Rules:\n"
    "- Cite every factual claim inline as [n], where n is the source number. "
    "If a claim draws on multiple sources, cite each, e.g. [1][3].\n"
    "- After your answer, on a new line, write exactly: "
    "Sources used: [n], [n], ... listing only the numbers you actually cited.\n"
    "- If the sources don't cover the question, say what's missing or what "
    "would be needed to answer, and do not guess. Do not use outside knowledge.\n"
    "- Be concise. Plain prose, no headers."
)


def _format_chunk(index: int, chunk: dict[str, Any]) -> str:
    title = chunk.get("title") or "(untitled)"
    college = chunk.get("college") or "(unknown college)"
    source = chunk.get("source") or ""
    header = f"[{index}] {title} — {college}"
    if source:
        header += f" ({source})"
    return f"{header}\n{chunk.get('text', '')}"


def _build_prompt(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Build the OpenAI Chat Completions `messages` payload.

    Chunks are numbered [1..N] in the same order they arrive (best-first), so
    the [n] tags the model emits map directly onto _build_sources()'s indexing.
    """
    formatted = "\n\n".join(_format_chunk(i + 1, c) for i, c in enumerate(chunks))
    user_message = (
        f"Question: {query}\n\n"
        f"Sources:\n{formatted}\n\n"
        "When you answer, cite each fact with the number of the source you used."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def _build_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact citation payload mirroring the [n] indexing used in the prompt."""
    return [
        {
            "index": i + 1,
            "title": chunk.get("title"),
            "college": chunk.get("college"),
            "category": chunk.get("category"),
            "source": chunk.get("source"),
        }
        for i, chunk in enumerate(chunks)
    ]


def generate_answer(
    query: str,
    n_results: int = 5,
    filters: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Run hybrid retrieval and synthesize a cited natural-language answer.

    Returns:
        {
            "answer":  str,                # model output, expected to contain [n] citations
            "sources": list[dict],         # [{index, title, college, category, source}, ...]
            "model":   str,                # model id actually used
        }

    Raises:
        RuntimeError: if no OpenAI API key is configured.
    """
    api_key = os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Set OPENAI_KEY (or OPENAI_API_KEY) "
            "in your environment or .env file."
        )

    chunks = retrieve(query=query, n_results=n_results, filters=filters)
    if not chunks:
        return {
            "answer": (
                "I couldn't find anything in the indexed CUNY documents that "
                "matches that question."
            ),
            "sources": [],
            "model": model or DEFAULT_MODEL,
        }

    messages = _build_prompt(query, chunks)
    chosen_model = model or DEFAULT_MODEL

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        temperature=0.2,
    )
    answer = (response.choices[0].message.content or "").strip()

    return {
        "answer": answer,
        "sources": _build_sources(chunks),
        "model": chosen_model,
    }
