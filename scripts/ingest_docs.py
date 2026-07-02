from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ruff: noqa: E402, I001
from app.ingestion.chunker import chunk_markdown  # noqa: E402
from app.ingestion.markdown import read_markdown  # noqa: E402
from app.ingestion.registry import (  # noqa: E402
    DEFAULT_REGISTRY_DOCUMENTS_DIR,
    existing_registry_documents,
    load_registry_documents,
)


OUTPUT_PATH = ROOT_DIR / "artifacts" / "chunks.jsonl"


def main() -> int:
    registry_dir = ROOT_DIR / DEFAULT_REGISTRY_DOCUMENTS_DIR
    documents = load_registry_documents(registry_dir)
    existing_documents, missing_documents = existing_registry_documents(
        documents,
        root_dir=ROOT_DIR,
    )

    chunks = []
    for document in existing_documents:
        content = read_markdown(ROOT_DIR / document.local_path)
        chunks.extend(chunk_markdown(document, content))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for chunk in chunks:
            output_file.write(
                json.dumps(chunk.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
            )

    print(f"registry documents found: {len(documents)}")
    print(f"local documents read: {len(existing_documents)}")
    print(f"chunks written: {len(chunks)}")
    print(f"missing documents: {len(missing_documents)}")
    if missing_documents:
        print("missing local paths:")
        for document in missing_documents:
            print(f"- {document.local_path.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
