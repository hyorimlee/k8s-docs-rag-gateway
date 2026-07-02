from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ruff: noqa: E402, I001
from app.retrieval.loader import DEFAULT_CHUNKS_PATH, load_chunks  # noqa: E402
from app.retrieval.simple import retrieve  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve local documentation chunks.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--chunks", type=Path, default=ROOT_DIR / DEFAULT_CHUNKS_PATH)
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    results = retrieve(args.query, chunks, top_k=args.top_k)

    for result in results:
        print(f"{result.score:.1f} {result.title}")
        print(f"  heading: {result.heading}")
        print(f"  path: {result.local_path}")
        print(f"  chunk_id: {result.chunk_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
