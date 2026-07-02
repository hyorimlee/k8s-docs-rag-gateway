from __future__ import annotations

from typing import Protocol

DEFAULT_MAX_CONTEXT_CHARS = 6000
NO_CONTEXT_MESSAGE = "No relevant documentation context was provided."


class PromptChunk(Protocol):
    chunk_id: str
    document_id: str
    title: str
    heading: str | None
    source_url: str | None
    local_path: str
    content: str
    score: float
    docs_version: str | None
    imported_commit: str | None


def build_prompt(
    question: str,
    retrieved_chunks: list[PromptChunk],
    *,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    context_block = _build_context_block(retrieved_chunks, max_context_chars)

    return "\n\n".join(
        [
            "SYSTEM / ASSISTANT BOUNDARY INSTRUCTIONS\n"
            "- You are a documentation-grounded Kubernetes assistant.\n"
            "- Use only the provided context.\n"
            "- Do not claim to inspect a live Kubernetes cluster.\n"
            "- Do not invent pod names, node names, events, IPs, namespaces, "
            "or secrets.\n"
            "- If the context is insufficient, say that the available documentation "
            "context is insufficient.\n"
            "- Prefer safe diagnostic guidance over destructive actions.\n"
            "- Do not recommend deleting workloads as a first step.\n"
            "- Do not expose or ask for secrets.",
            f"CONTEXT\n{context_block}",
            f"USER QUESTION\n{question}",
            "OUTPUT GUIDANCE\n"
            "- Answer concisely.\n"
            "- Cite sources by source number, for example [1].\n"
            "- Mention uncertainty when the context is insufficient.",
        ]
    )


def _build_context_block(
    retrieved_chunks: list[PromptChunk],
    max_context_chars: int,
) -> str:
    if not retrieved_chunks:
        return (
            f"{NO_CONTEXT_MESSAGE}\nDo not fabricate an answer from general knowledge."
        )

    remaining_chars = max(0, max_context_chars)
    source_blocks: list[str] = []

    for source_number, chunk in enumerate(retrieved_chunks, start=1):
        metadata = _format_metadata(source_number, chunk)
        content = _truncate_content(chunk.content, remaining_chars)
        remaining_chars -= len(content)
        source_blocks.append(f"{metadata}\ncontent:\n{content}")

        if remaining_chars <= 0:
            remaining_chars = 0

    return "\n\n".join(source_blocks)


def _format_metadata(source_number: int, chunk: PromptChunk) -> str:
    return "\n".join(
        [
            f"[{source_number}]",
            f"chunk_id: {chunk.chunk_id}",
            f"document_id: {chunk.document_id}",
            f"title: {chunk.title}",
            f"heading: {_display_value(chunk.heading)}",
            f"source_url: {_display_value(chunk.source_url)}",
            f"local_path: {chunk.local_path}",
            f"score: {chunk.score:.1f}",
            f"docs_version: {_display_value(chunk.docs_version)}",
            f"imported_commit: {_display_value(chunk.imported_commit)}",
        ]
    )


def _truncate_content(content: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(content) <= max_chars:
        return content
    if max_chars <= 15:
        return content[:max_chars]
    return f"{content[: max_chars - 15].rstrip()}\n[truncated]"


def _display_value(value: str | None) -> str:
    if value is None:
        return "null"
    return value
