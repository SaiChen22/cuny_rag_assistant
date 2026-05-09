"""CLI entry point: ask the CUNY RAG assistant a single question."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Make `src/pipeline/generator.py` importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src" / "pipeline"))
from generator import generate_answer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask the CUNY RAG assistant a question."
    )
    parser.add_argument("query", type=str, help="Natural-language question.")
    parser.add_argument("--n-results", type=int, default=5)
    parser.add_argument("--college", type=str, default=None)
    parser.add_argument("--category", type=str, default=None)
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the OpenAI model (defaults to OPENAI_MODEL or gpt-4o-mini).",
    )
    args = parser.parse_args()

    filters: dict[str, Any] = {}
    if args.college:
        filters["college"] = args.college
    if args.category:
        filters["category"] = args.category

    try:
        result = generate_answer(
            query=args.query,
            n_results=args.n_results,
            filters=filters or None,
            model=args.model,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(result["answer"])

    sources = result["sources"]
    if sources:
        print("\nSources:")
        for src in sources:
            label = src.get("title") or "(no title)"
            college = src.get("college") or ""
            print(f"  [{src['index']}] {label} — {college}".rstrip(" —"))
            if src.get("source"):
                print(f"      {src['source']}")

    print(f"\n(model: {result['model']})")


if __name__ == "__main__":
    main()
