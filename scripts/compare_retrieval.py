from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.retrieval.loader import load_chunks  # noqa: E402
from app.retrieval.simple import retrieve  # noqa: E402
from app.retrieval.vector import ChromaVectorRetriever, build_vector_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare keyword and vector retrieval")
    parser.add_argument("query", help="Query to evaluate")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--persist-directory", default="artifacts/chroma")
    parser.add_argument("--chunks-path", default="artifacts/chunks.jsonl")
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
    args = parser.parse_args()

    chunks_path = ROOT_DIR / args.chunks_path
    persist_directory = ROOT_DIR / args.persist_directory
    chunks = load_chunks(chunks_path)
    keyword_results = retrieve(args.query, chunks, top_k=args.top_k)
    build_vector_index(
        chunks,
        persist_directory=persist_directory,
        embedding_provider=args.embedding_provider,
        model_name=args.model_name,
    )
    vector_retriever = ChromaVectorRetriever(
        persist_directory=persist_directory,
        embedding_provider=args.embedding_provider,
        model_name=args.model_name,
    )
    vector_results = vector_retriever.retrieve(args.query, chunks, top_k=args.top_k)

    print(f"query: {args.query}")
    print("keyword:")
    for result in keyword_results:
        print(f"  - {result.document_id}: {result.title} (score={result.score})")
    print("vector:")
    for result in vector_results:
        print(f"  - {result.document_id}: {result.title} (score={result.score})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
