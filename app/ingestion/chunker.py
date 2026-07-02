from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path

from app.ingestion.registry import RegistryDocument

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    title: str
    source_url: str | None
    local_path: str
    docs_version: str | None
    imported_commit: str | None
    heading: str | None
    content: str
    collection_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    priority: str | None = None
    language: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MarkdownSection:
    heading: str | None
    content: str


def chunk_markdown(document: RegistryDocument, content: str) -> list[DocumentChunk]:
    sections = split_by_headings(content)
    chunks: list[DocumentChunk] = []

    for index, section in enumerate(sections):
        chunk_content = section.content.strip()
        if not chunk_content:
            continue

        chunks.append(
            DocumentChunk(
                chunk_id=_chunk_id(document.document_id, index, section.heading),
                document_id=document.document_id,
                title=document.title,
                source_url=document.source_url,
                local_path=_path_string(document.local_path),
                docs_version=document.docs_version,
                imported_commit=document.imported_commit,
                heading=section.heading,
                content=chunk_content,
                collection_ids=document.collection_ids,
                tags=document.tags,
                category=document.category,
                priority=document.priority,
                language=document.language,
            )
        )

    return chunks


def split_by_headings(content: str) -> list[MarkdownSection]:
    sections: list[MarkdownSection] = []
    heading_stack: list[tuple[int, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in content.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            _append_section(sections, current_heading, current_lines)
            current_lines = [line]

            level = len(match.group(1))
            text = match.group(2).strip()
            heading_stack = [
                (heading_level, heading_text)
                for heading_level, heading_text in heading_stack
                if heading_level < level
            ]
            heading_stack.append((level, text))
            current_heading = " > ".join(heading for _, heading in heading_stack)
            continue

        current_lines.append(line)

    _append_section(sections, current_heading, current_lines)
    return sections


def _append_section(
    sections: list[MarkdownSection],
    heading: str | None,
    lines: list[str],
) -> None:
    content = "\n".join(lines).strip()
    if content and not _is_heading_only_section(lines):
        sections.append(MarkdownSection(heading=heading, content=content))


def _is_heading_only_section(lines: list[str]) -> bool:
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    return len(non_empty_lines) == 1 and bool(HEADING_PATTERN.match(non_empty_lines[0]))


def _chunk_id(document_id: str, index: int, heading: str | None) -> str:
    seed = f"{document_id}:{index}:{heading or ''}"
    digest = sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"{document_id}-{index:04d}-{digest}"


def _path_string(path: Path) -> str:
    return path.as_posix()
