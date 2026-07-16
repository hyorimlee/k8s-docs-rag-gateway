from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.retrieval.loader import load_chunks  # noqa: E402
from app.retrieval.vector import build_vector_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local Chroma-backed index")
    parser.add_argument(
        "--chunks-path",
        default="artifacts/chunks.jsonl",
        help="Path to the chunks JSONL artifact",
    )
    parser.add_argument(
        "--persist-directory",
        default="artifacts/chroma",
        help="Path where the local Chroma data is stored",
    )
    parser.add_argument(
        "--embedding-provider",
        default="hash",
        choices=["hash", "sentence-transformers"],
        help="Embedding provider to use",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Optional model name for semantic embeddings",
    )
    parser.add_argument(
        "--collection-name",
        default="k8s_docs_chunks",
        help="Chroma collection name",
    )
    args = parser.parse_args()

    chunks_path = ROOT_DIR / args.chunks_path
    persist_directory = ROOT_DIR / args.persist_directory
    if not chunks_path.exists():
        raise SystemExit(
            "Chunks artifact not found. Run "
            "'.venv/bin/python scripts/ingest_docs.py' first."
        )

    chunks = load_chunks(chunks_path)
    summary = build_vector_index(
        chunks,
        persist_directory=persist_directory,
        embedding_provider=args.embedding_provider,
        collection_name=args.collection_name,
        model_name=args.model_name,
    )

    print(f"chunks read: {summary['chunks_read']}")
    print(f"vectors indexed: {summary['vectors_indexed']}")
    print(f"collection: {summary['collection']}")
    print(f"persist_directory: {summary['persist_directory']}")
    print(f"embedding_provider: {summary['embedding_provider']}")
    if summary.get("embedding_model"):
        print(f"embedding_model: {summary['embedding_model']}")
    if summary.get("embedding_dimension") is not None:
        print(f"embedding_dimension: {summary['embedding_dimension']}")
    if summary.get("distance_metric"):
        print(f"distance_metric: {summary['distance_metric']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
