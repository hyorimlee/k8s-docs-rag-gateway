from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY_DOCUMENTS_DIR = Path("docs_source/registry/documents")


@dataclass(frozen=True)
class RegistryDocument:
    document_id: str
    title: str
    source_url: str | None
    local_path: Path
    docs_version: str | None
    imported_commit: str | None
    collection_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    priority: str | None = None
    language: str | None = None


def load_registry_documents(
    registry_documents_dir: Path = DEFAULT_REGISTRY_DOCUMENTS_DIR,
) -> list[RegistryDocument]:
    documents: list[RegistryDocument] = []

    for registry_file in sorted(registry_documents_dir.glob("*.yaml")):
        raw = yaml.safe_load(registry_file.read_text(encoding="utf-8")) or {}
        for entry in raw.get("documents", []):
            documents.append(_normalize_document(entry))

    return documents


def existing_registry_documents(
    documents: list[RegistryDocument],
    root_dir: Path = Path("."),
) -> tuple[list[RegistryDocument], list[RegistryDocument]]:
    existing: list[RegistryDocument] = []
    missing: list[RegistryDocument] = []

    for document in documents:
        if (root_dir / document.local_path).exists():
            existing.append(document)
        else:
            missing.append(document)

    return existing, missing


def _normalize_document(entry: dict[str, Any]) -> RegistryDocument:
    return RegistryDocument(
        document_id=str(entry["id"]),
        title=str(entry["title"]),
        source_url=entry.get("source_url"),
        local_path=Path(str(entry["local_path"])),
        docs_version=_optional_string(entry.get("docs_version")),
        imported_commit=_optional_string(entry.get("imported_commit")),
        collection_ids=list(entry.get("collection_ids") or []),
        tags=list(entry.get("tags") or []),
        category=_optional_string(entry.get("category")),
        priority=_optional_string(entry.get("priority")),
        language=_optional_string(entry.get("language")),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
