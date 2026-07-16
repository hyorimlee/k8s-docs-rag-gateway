from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.mock import CONTEXT_RESPONSE_INTRO, MOCK_PROVIDER_NOTE
from app.retrieval.vector import build_vector_index
from app.tracing.store import clear_traces

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_trace_store() -> Iterator[None]:
    clear_traces()
    yield
    clear_traces()


def test_successful_chat_saves_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(
        chunks_path,
        [
            {
                "chunk_id": "chunk-pending",
                "document_id": "doc-pending",
                "title": "Pod Pending Troubleshooting",
                "heading": "Pod Pending Troubleshooting > Safe Triage Flow",
                "source_url": "https://example.com/pods",
                "local_path": "docs/pending.md",
                "docs_version": "local",
                "imported_commit": "abc123",
                "collection_ids": ["pod-pending-troubleshooting"],
                "tags": ["pod-pending", "scheduling"],
                "category": "custom-runbook",
                "priority": "p0",
                "language": "en",
                "content": "Pending Pods can wait for scheduling constraints.",
            }
        ],
    )
    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", chunks_path)

    chat_response = client.post(
        "/chat",
        json={"message": "Why is my pod pending scheduling?", "top_k": 1},
    )

    assert chat_response.status_code == 200
    request_id = chat_response.json()["request_id"]
    trace_response = client.get(f"/traces/{request_id}")

    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["request_id"] == request_id
    assert trace["question"] == "Why is my pod pending scheduling?"
    assert CONTEXT_RESPONSE_INTRO in trace["answer"]
    assert MOCK_PROVIDER_NOTE in trace["answer"]
    assert trace["sources"] == chat_response.json()["sources"]
    assert trace["retrieved_chunks"][0]["chunk_id"] == "chunk-pending"
    assert trace["retrieved_chunks"][0]["content"] == (
        "Pending Pods can wait for scheduling constraints."
    )
    assert "USER QUESTION\nWhy is my pod pending scheduling?" in trace["prompt"]
    assert trace["model"] == "mock"
    assert trace["token_usage"] == chat_response.json()["token_usage"]
    assert trace["latency_ms"] >= 0
    assert trace["fallback"] is False
    assert trace["error_type"] is None
    assert trace["created_at"]


def test_vector_chat_trace_records_embedding_provider_and_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSentenceTransformerModel:
        def encode_document(self, text: str) -> list[float]:
            return [1.0, 0.0]

        def encode_query(self, text: str) -> list[float]:
            return [1.0, 0.0]

    module = type(
        "SentenceTransformersModule",
        (),
        {"SentenceTransformer": lambda *args, **kwargs: FakeSentenceTransformerModel()},
    )()
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(
        chunks_path,
        [
            {
                "chunk_id": "chunk-hpa",
                "document_id": "doc-hpa",
                "title": "Horizontal Pod Autoscaling",
                "heading": "Horizontal Pod Autoscaling > Capacity Boundary",
                "source_url": "https://example.com/hpa",
                "local_path": "docs/hpa.md",
                "docs_version": "local",
                "imported_commit": "abc123",
                "collection_ids": ["autoscaling"],
                "tags": ["hpa"],
                "category": "workloads",
                "priority": "p0",
                "language": "en",
                "content": "Autoscaling adds replicas when CPU usage rises.",
            }
        ],
    )
    persist_directory = tmp_path / "chroma"
    build_vector_index(
        [
            {
                "chunk_id": "chunk-hpa",
                "document_id": "doc-hpa",
                "title": "Horizontal Pod Autoscaling",
                "heading": "Horizontal Pod Autoscaling > Capacity Boundary",
                "source_url": "https://example.com/hpa",
                "local_path": "docs/hpa.md",
                "docs_version": "local",
                "imported_commit": "abc123",
                "collection_ids": ["autoscaling"],
                "tags": ["hpa"],
                "category": "workloads",
                "priority": "p0",
                "language": "en",
                "content": "Autoscaling adds replicas when CPU usage rises.",
            }
        ],
        persist_directory=persist_directory,
        embedding_provider="sentence-transformers",
        model_name="sentence-transformers/demo-model",
    )

    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", chunks_path)
    monkeypatch.setattr("app.services.chat.CHROMA_PERSIST_DIRECTORY", persist_directory)

    chat_response = client.post(
        "/chat",
        json={
            "message": "How can Kubernetes add more replicas when CPU usage rises?",
            "top_k": 1,
            "retrieval_mode": "vector",
        },
    )

    assert chat_response.status_code == 200
    request_id = chat_response.json()["request_id"]
    trace_response = client.get(f"/traces/{request_id}")

    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["retrieval_mode"] == "vector"
    assert trace["embedding_provider"] == "sentence-transformers"
    assert trace["embedding_model"] == "sentence-transformers/demo-model"


def test_missing_trace_returns_404() -> None:
    response = client.get("/traces/not-a-real-request")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trace not found"


def test_fallback_chat_saves_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", tmp_path / "missing.jsonl")

    chat_response = client.post("/chat", json={"message": "How do I check pods?"})

    assert chat_response.status_code == 200
    chat_body = chat_response.json()
    trace_response = client.get(f"/traces/{chat_body['request_id']}")

    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["request_id"] == chat_body["request_id"]
    assert trace["question"] == "How do I check pods?"
    assert trace["answer"] == chat_body["answer"]
    assert trace["sources"] == []
    assert trace["retrieved_chunks"] == []
    assert trace["prompt"] == ""
    assert trace["token_usage"] == chat_body["token_usage"]
    assert trace["latency_ms"] >= 0
    assert trace["fallback"] is True
    assert trace["error_type"] == "chunks_not_found"


def write_chunks(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as chunks_file:
        for row in rows:
            chunks_file.write(json.dumps(row) + "\n")
