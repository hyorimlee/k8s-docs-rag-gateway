from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.mock import MOCK_PROVIDER_TEXT
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
    assert trace["answer"] == MOCK_PROVIDER_TEXT
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
