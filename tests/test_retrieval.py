from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ingestion.chunker import chunk_markdown
from app.ingestion.markdown import read_markdown
from app.ingestion.registry import load_registry_documents
from app.retrieval.loader import ChunkRecord, load_chunks
from app.retrieval.simple import retrieve


def test_loader_reads_jsonl_chunks(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(
        chunks_path,
        [
            {
                "chunk_id": "chunk-a",
                "document_id": "doc-a",
                "title": "Pods",
                "heading": "Pods > Scheduling",
                "source_url": "https://example.com/pods",
                "local_path": "docs/pods.md",
                "docs_version": "local",
                "imported_commit": None,
                "collection_ids": ["workloads"],
                "tags": ["pod", "scheduling"],
                "category": "workloads",
                "priority": "p0",
                "language": "en",
                "content": "A Pod can remain Pending before it is scheduled.",
            }
        ],
    )

    chunks = load_chunks(chunks_path)

    assert chunks == [
        ChunkRecord(
            chunk_id="chunk-a",
            document_id="doc-a",
            title="Pods",
            heading="Pods > Scheduling",
            source_url="https://example.com/pods",
            local_path="docs/pods.md",
            docs_version="local",
            imported_commit=None,
            collection_ids=["workloads"],
            tags=["pod", "scheduling"],
            category="workloads",
            priority="p0",
            language="en",
            content="A Pod can remain Pending before it is scheduled.",
        )
    ]


def test_loader_missing_file_has_clear_exception(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.jsonl"

    with pytest.raises(FileNotFoundError, match="Run scripts/ingest_docs.py first"):
        load_chunks(missing_path)


def test_retriever_returns_relevant_chunks_for_content_match() -> None:
    chunks = fixture_chunks()

    results = retrieve("why is pod pending", chunks, top_k=3)

    assert [result.chunk_id for result in results] == ["chunk-pending", "chunk-tag"]
    assert results[0].content == "Pending Pods often wait for scheduler placement."
    assert results[0].local_path == "docs/pending.md"


def test_heading_and_title_matches_receive_boost() -> None:
    chunks = [
        chunk(
            "chunk-content",
            title="General",
            heading="General",
            content="CronJob CronJob CronJob",
        ),
        chunk(
            "chunk-heading",
            title="CronJob Backfill Safety",
            heading="CronJob Backfill Safety > Purpose",
            content="Scheduled work overview.",
        ),
    ]

    results = retrieve("cronjob", chunks, top_k=2)

    assert [result.chunk_id for result in results] == ["chunk-heading", "chunk-content"]
    assert results[0].score > results[1].score


def test_tag_matches_receive_boost() -> None:
    chunks = [
        chunk(
            "chunk-content",
            title="General",
            heading="General",
            tags=[],
            content="Backfill Backfill",
        ),
        chunk(
            "chunk-tag",
            title="Checklist",
            heading="Checklist",
            tags=["backfill"],
            content="Safe planning flow.",
        ),
    ]

    results = retrieve("backfill", chunks, top_k=2)

    assert [result.chunk_id for result in results] == ["chunk-tag", "chunk-content"]


def test_top_k_limits_result_count() -> None:
    results = retrieve("pod", fixture_chunks(), top_k=1)

    assert len(results) == 1


def test_results_are_deterministic_for_ties() -> None:
    chunks = [
        chunk("chunk-b", content="Pod scheduling"),
        chunk("chunk-a", content="Pod scheduling"),
    ]

    results = retrieve("pod", chunks, top_k=2)

    assert [result.chunk_id for result in results] == ["chunk-a", "chunk-b"]


def test_retriever_ignores_common_question_stopwords() -> None:
    chunks = [
        chunk(
            "chunk-k8s",
            content="Avoid exposing raw secrets in chat.",
        )
    ]

    results = retrieve("How do I improve my sourdough starter?", chunks, top_k=3)

    assert results == []


@pytest.mark.parametrize(
    ("query", "expected_document_ids"),
    [
        (
            "Horizontal Pod Autoscaler",
            {"k8s-horizontal-pod-autoscaling"},
        ),
        ("Kubernetes Secret", {"k8s-secrets"}),
        ("ConfigMap", {"k8s-configmaps"}),
        ("Pod lifecycle", {"k8s-pod-lifecycle"}),
        (
            "taints and tolerations",
            {"k8s-taints-and-tolerations"},
        ),
        (
            "resource requests limits",
            {"k8s-resource-management"},
        ),
        (
            "How do I configure a CronJob schedule?",
            {"k8s-cronjobs", "custom-cronjob-backfill-checklist"},
        ),
        (
            "Why is my Pod pending because of node affinity or taints?",
            {
                "k8s-assign-pods-to-nodes",
                "k8s-taints-and-tolerations",
                "custom-pod-pending-troubleshooting",
            },
        ),
    ],
)
def test_retriever_finds_imported_kubernetes_docs(
    query: str,
    expected_document_ids: set[str],
) -> None:
    chunks = imported_corpus_chunks()

    results = retrieve(query, chunks, top_k=5)
    result_document_ids = {result.document_id for result in results}

    assert result_document_ids.intersection(expected_document_ids)


def fixture_chunks() -> list[ChunkRecord]:
    return [
        chunk(
            "chunk-pending",
            document_id="doc-pending",
            title="Pod Pending Troubleshooting",
            heading="Pod Pending Troubleshooting > Safe Triage Flow",
            tags=["pod-pending", "scheduling"],
            content="Pending Pods often wait for scheduler placement.",
            local_path="docs/pending.md",
        ),
        chunk(
            "chunk-cron",
            document_id="doc-cron",
            title="CronJob Backfill",
            heading="CronJob Backfill > Purpose",
            tags=["cronjob", "backfill"],
            content="Backfill Jobs should avoid duplicate processing.",
            local_path="docs/cron.md",
        ),
        chunk(
            "chunk-tag",
            document_id="doc-tag",
            title="Scheduling Checklist",
            heading="Scheduling Checklist",
            tags=["pod"],
            content="Check node capacity.",
            local_path="docs/tag.md",
        ),
    ]


def imported_corpus_chunks() -> list[ChunkRecord]:
    chunks = []
    for document in load_registry_documents():
        if document.local_path.exists():
            content = read_markdown(document.local_path)
            chunks.extend(
                ChunkRecord(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    heading=chunk.heading,
                    source_url=chunk.source_url,
                    local_path=chunk.local_path,
                    docs_version=chunk.docs_version,
                    imported_commit=chunk.imported_commit,
                    collection_ids=chunk.collection_ids,
                    tags=chunk.tags,
                    category=chunk.category,
                    priority=chunk.priority,
                    language=chunk.language,
                    content=chunk.content,
                )
                for chunk in chunk_markdown(document, content)
            )
    return chunks


def chunk(
    chunk_id: str,
    *,
    document_id: str = "doc",
    title: str = "Title",
    heading: str | None = "Title",
    source_url: str | None = None,
    local_path: str = "docs/example.md",
    docs_version: str | None = "local",
    imported_commit: str | None = None,
    collection_ids: list[str] | None = None,
    tags: list[str] | None = None,
    category: str | None = "custom",
    priority: str | None = "p0",
    language: str | None = "en",
    content: str = "",
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        title=title,
        heading=heading,
        source_url=source_url,
        local_path=local_path,
        docs_version=docs_version,
        imported_commit=imported_commit,
        collection_ids=collection_ids or [],
        tags=tags or [],
        category=category,
        priority=priority,
        language=language,
        content=content,
    )


def write_chunks(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as chunks_file:
        for row in rows:
            chunks_file.write(json.dumps(row) + "\n")
