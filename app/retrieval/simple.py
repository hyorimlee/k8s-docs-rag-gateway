from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from app.retrieval.loader import ChunkRecord

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
CONTENT_WEIGHT = 1.0
HEADING_TITLE_WEIGHT = 3.0
TAG_WEIGHT = 2.0


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    document_id: str
    title: str
    heading: str | None
    source_url: str | None
    local_path: str
    score: float
    content: str
    docs_version: str | None = None
    imported_commit: str | None = None
    collection_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    priority: str | None = None
    language: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def retrieve(
    query: str,
    chunks: list[ChunkRecord],
    *,
    top_k: int = 5,
) -> list[RetrievalResult]:
    if top_k <= 0:
        return []

    query_tokens = set(tokenize(query))
    if not query_tokens:
        return []

    scored_results = [
        _to_result(chunk, score)
        for chunk in chunks
        if (score := score_chunk(query_tokens, chunk)) > 0
    ]
    scored_results.sort(key=lambda result: (-result.score, result.chunk_id))
    return scored_results[:top_k]


def score_chunk(query_tokens: set[str], chunk: ChunkRecord) -> float:
    content_score = (
        _overlap_count(query_tokens, tokenize(chunk.content)) * CONTENT_WEIGHT
    )
    heading_title_score = (
        _overlap_count(query_tokens, tokenize(chunk.heading or ""))
        + _overlap_count(query_tokens, tokenize(chunk.title))
    ) * HEADING_TITLE_WEIGHT
    tag_score = _overlap_count(query_tokens, _tag_tokens(chunk.tags)) * TAG_WEIGHT

    return content_score + heading_title_score + tag_score


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _overlap_count(query_tokens: set[str], candidate_tokens: list[str]) -> int:
    return len(query_tokens.intersection(candidate_tokens))


def _tag_tokens(tags: list[str]) -> list[str]:
    tokens: list[str] = []
    for tag in tags:
        tokens.extend(tokenize(tag))
    return tokens


def _to_result(chunk: ChunkRecord, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        title=chunk.title,
        heading=chunk.heading,
        source_url=chunk.source_url,
        local_path=chunk.local_path,
        score=score,
        content=chunk.content,
        docs_version=chunk.docs_version,
        imported_commit=chunk.imported_commit,
        collection_ids=chunk.collection_ids,
        tags=chunk.tags,
        category=chunk.category,
        priority=chunk.priority,
        language=chunk.language,
    )
