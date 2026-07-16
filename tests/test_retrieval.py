from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.ingestion.chunker import chunk_markdown
from app.ingestion.markdown import read_markdown
from app.ingestion.registry import load_registry_documents
from app.retrieval.loader import ChunkRecord, load_chunks
from app.retrieval.simple import retrieve
from app.retrieval.vector import (
    ChromaVectorRetriever,
    SentenceTransformerEmbeddingProvider,
    VectorRetrievalError,
    build_vector_index,
)


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


def test_build_vector_index_persists_local_chroma_collection(tmp_path: Path) -> None:
    chunks = fixture_chunks()
    persist_directory = tmp_path / "chroma"

    summary = build_vector_index(
        chunks,
        persist_directory=persist_directory,
        embedding_provider="hash",
    )

    assert summary["vectors_indexed"] == len(chunks)
    assert summary["collection"] == "k8s_docs_chunks"
    assert summary["persist_directory"] == str(persist_directory)
    assert persist_directory.exists()


def test_vector_retriever_returns_top_k_results_with_metadata(tmp_path: Path) -> None:
    chunks = fixture_chunks()
    persist_directory = tmp_path / "chroma"
    build_vector_index(
        chunks,
        persist_directory=persist_directory,
        embedding_provider="hash",
    )

    retriever = ChromaVectorRetriever(
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    results = retriever.retrieve("pending pods", chunks, top_k=2)

    assert [result.chunk_id for result in results] == ["chunk-pending", "chunk-tag"]
    assert results[0].retrieval_mode == "vector"
    assert results[0].score > 0
    assert results[0].title == "Pod Pending Troubleshooting"


def test_sentence_transformer_provider_uses_document_and_query_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeSentenceTransformerModel()
    module = type(
        "SentenceTransformersModule",
        (),
        {"SentenceTransformer": lambda *args, **kwargs: fake_model},
    )()
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", module)

    provider = SentenceTransformerEmbeddingProvider(model_name="demo-model")
    documents = provider.embed_documents(["alpha", "beta"])
    query = provider.embed_query("gamma")

    assert documents == [[1.0, 0.0], [0.0, 1.0]]
    assert query == [1.0, 0.0]
    assert fake_model.document_calls == ["alpha", "beta"]
    assert fake_model.query_calls == ["gamma"]
    assert provider.model is fake_model


def test_sentence_transformer_provider_requires_optional_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", None)

    provider = SentenceTransformerEmbeddingProvider(model_name="demo-model")
    with pytest.raises(VectorRetrievalError, match="Optional dependency missing"):
        provider.embed_query("demo")


def test_build_vector_index_records_semantic_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model = FakeSentenceTransformerModel()
    module = type(
        "SentenceTransformersModule",
        (),
        {"SentenceTransformer": lambda *args, **kwargs: fake_model},
    )()
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", module)

    summary = build_vector_index(
        fixture_chunks(),
        persist_directory=tmp_path / "chroma",
        embedding_provider="sentence-transformers",
        model_name="sentence-transformers/demo-model",
    )

    assert summary["embedding_provider"] == "sentence-transformers"
    assert summary["embedding_model"] == "sentence-transformers/demo-model"
    assert summary["embedding_dimension"] == 2
    assert summary["distance_metric"] == "cosine"


def test_vector_retrieval_uses_chroma_query_api_for_top_k(tmp_path: Path) -> None:
    chunks = fixture_chunks()
    persist_directory = tmp_path / "chroma"
    build_vector_index(
        chunks,
        persist_directory=persist_directory,
        embedding_provider="hash",
    )

    retriever = ChromaVectorRetriever(
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    results = retriever.retrieve("pending pods", chunks, top_k=1)

    assert len(results) == 1
    assert results[0].retrieval_mode == "vector"
    assert results[0].score >= 0.0


def test_vector_retriever_rejects_incompatible_index_provider_or_dimension(
    tmp_path: Path,
) -> None:
    chunks = fixture_chunks()
    persist_directory = tmp_path / "chroma"
    build_vector_index(
        chunks,
        persist_directory=persist_directory,
        embedding_provider="hash",
    )

    retriever = ChromaVectorRetriever(
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    retriever._provider = type(
        "Provider",
        (),
        {"embed_query": lambda self, text: [0.0] * 8},
    )()  # type: ignore[assignment]

    with pytest.raises(VectorRetrievalError, match="incompatible"):
        retriever.retrieve("pending pods", chunks, top_k=1)


def test_vector_index_rebuild_removes_stale_chunks(tmp_path: Path) -> None:
    persist_directory = tmp_path / "chroma"
    build_vector_index(
        [chunk("chunk-a", content="alpha"), chunk("chunk-b", content="beta")],
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    build_vector_index(
        [chunk("chunk-a", content="alpha")],
        persist_directory=persist_directory,
        embedding_provider="hash",
    )

    retriever = ChromaVectorRetriever(
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    results = retriever.retrieve("alpha", [], top_k=5)

    assert [result.chunk_id for result in results] == ["chunk-a"]


class FakeSentenceTransformerModel:
    def __init__(self) -> None:
        self.document_calls: list[str] = []
        self.query_calls: list[str] = []

    def encode_document(self, text: str) -> list[float]:
        self.document_calls.append(text)
        if text == "alpha":
            return [1.0, 0.0]
        if text == "beta":
            return [0.0, 1.0]
        return [0.0, 0.0]

    def encode_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return [1.0, 0.0]


def test_compare_retrieval_cli_accepts_embedding_provider_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "compare_retrieval.py"
    )
    spec = importlib.util.spec_from_file_location("compare_retrieval", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    captured: dict[str, object] = {}

    monkeypatch.setattr(module, "load_chunks", lambda path: ["chunk"])
    monkeypatch.setattr(module, "retrieve", lambda query, chunks, top_k=3: [])

    def fake_build_vector_index(chunks, **kwargs):
        captured["build_kwargs"] = kwargs
        return {"chunks_read": 1, "vectors_indexed": 1}

    class FakeRetriever:
        def __init__(self, **kwargs):
            captured["retriever_kwargs"] = kwargs

        def retrieve(self, query, chunks, top_k=3):
            return []

    monkeypatch.setattr(module, "build_vector_index", fake_build_vector_index)
    monkeypatch.setattr(module, "ChromaVectorRetriever", FakeRetriever)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_retrieval.py",
            "pod pending",
            "--top-k",
            "2",
            "--embedding-provider",
            "sentence-transformers",
            "--model-name",
            "demo-model",
        ],
    )

    exit_code = module.main()

    assert exit_code == 0
    assert captured["build_kwargs"]["embedding_provider"] == "sentence-transformers"
    assert captured["build_kwargs"]["model_name"] == "demo-model"
    assert captured["retriever_kwargs"]["embedding_provider"] == "sentence-transformers"
    assert captured["retriever_kwargs"]["model_name"] == "demo-model"


def test_vector_metadata_round_trip_preserves_lists_and_nullable_fields(
    tmp_path: Path,
) -> None:
    chunk_record = chunk(
        "chunk-round-trip",
        document_id="doc-round-trip",
        title="Round Trip",
        heading="Round Trip > Details",
        source_url="https://example.com/round-trip",
        local_path="docs/round-trip.md",
        docs_version="v1",
        imported_commit="abc123",
        collection_ids=["alpha", "beta"],
        tags=["tag-a", "tag-b"],
        category="custom",
        priority="p1",
        language="en",
        content="Round trip metadata.",
    )
    persist_directory = tmp_path / "chroma"
    build_vector_index(
        [chunk_record],
        persist_directory=persist_directory,
        embedding_provider="hash",
    )

    retriever = ChromaVectorRetriever(
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    results = retriever.retrieve("round trip", [chunk_record], top_k=1)

    assert len(results) == 1
    assert results[0].chunk_id == "chunk-round-trip"
    assert results[0].collection_ids == ["alpha", "beta"]
    assert results[0].tags == ["tag-a", "tag-b"]
    assert results[0].source_url == "https://example.com/round-trip"
    assert results[0].docs_version == "v1"
    assert results[0].imported_commit == "abc123"


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
