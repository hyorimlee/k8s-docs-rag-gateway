from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CHUNKS_PATH = Path("artifacts/chunks.jsonl")


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    title: str
    heading: str | None
    source_url: str | None
    local_path: str
    content: str
    docs_version: str | None = None
    imported_commit: str | None = None
    collection_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    priority: str | None = None
    language: str | None = None


def load_chunks(path: Path = DEFAULT_CHUNKS_PATH) -> list[ChunkRecord]:
    if not path.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {path}. Run scripts/ingest_docs.py first."
        )

    chunks: list[ChunkRecord] = []
    with path.open(encoding="utf-8") as chunks_file:
        for line_number, line in enumerate(chunks_file, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in chunks file {path} at line {line_number}."
                ) from exc
            chunks.append(_normalize_chunk(raw, path, line_number))

    return chunks


def _normalize_chunk(raw: dict[str, Any], path: Path, line_number: int) -> ChunkRecord:
    try:
        return ChunkRecord(
            chunk_id=str(raw["chunk_id"]),
            document_id=str(raw["document_id"]),
            title=str(raw["title"]),
            heading=_optional_string(raw.get("heading")),
            source_url=_optional_string(raw.get("source_url")),
            local_path=str(raw["local_path"]),
            content=str(raw["content"]),
            docs_version=_optional_string(raw.get("docs_version")),
            imported_commit=_optional_string(raw.get("imported_commit")),
            collection_ids=list(raw.get("collection_ids") or []),
            tags=list(raw.get("tags") or []),
            category=_optional_string(raw.get("category")),
            priority=_optional_string(raw.get("priority")),
            language=_optional_string(raw.get("language")),
        )
    except KeyError as exc:
        raise ValueError(
            f"Missing required chunk field {exc} in {path} at line {line_number}."
        ) from exc


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
