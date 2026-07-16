from __future__ import annotations

import json
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from app.main import app
from app.providers.base import ProviderResponse
from app.providers.mock import (
    CONTEXT_RESPONSE_INTRO,
    MOCK_PROVIDER_NOTE,
    NO_CONTEXT_RESPONSE,
)
from app.retrieval.vector import build_vector_index
from app.schemas import ChatRequest
from app.services.chat import handle_chat

client = TestClient(app)


def test_chat_returns_mock_rag_response_with_sources(
    tmp_path: Path,
    monkeypatch,
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
            },
            {
                "chunk_id": "chunk-cron",
                "document_id": "doc-cron",
                "title": "CronJob Backfill",
                "heading": "CronJob Backfill > Purpose",
                "source_url": None,
                "local_path": "docs/cron.md",
                "content": "Backfill Jobs should avoid duplicate work.",
            },
        ],
    )
    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", chunks_path)

    response = client.post(
        "/chat",
        json={
            "user_id": "user-1",
            "session_id": "session-1",
            "message": "Why is my pod pending scheduling?",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert CONTEXT_RESPONSE_INTRO in body["answer"]
    assert "Pod Pending Troubleshooting" in body["answer"]
    assert MOCK_PROVIDER_NOTE in body["answer"]
    assert body["model"] == "mock"
    assert body["fallback"] is False
    assert body["error_type"] is None
    assert body["latency_ms"] >= 0
    assert body["token_usage"]["input_tokens"] > 0
    assert body["token_usage"]["output_tokens"] == len(body["answer"].split())
    assert body["token_usage"]["total_tokens"] == (
        body["token_usage"]["input_tokens"] + body["token_usage"]["output_tokens"]
    )
    assert body["sources"] == [
        {
            "chunk_id": "chunk-pending",
            "document_id": "doc-pending",
            "title": "Pod Pending Troubleshooting",
            "heading": "Pod Pending Troubleshooting > Safe Triage Flow",
            "source_url": "https://example.com/pods",
            "local_path": "docs/pending.md",
            "score": 20.0,
            "docs_version": "local",
            "imported_commit": "abc123",
        }
    ]


def test_chat_handles_missing_chunks_file_safely(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", tmp_path / "missing.jsonl")

    response = client.post("/chat", json={"message": "How do I check pod status?"})

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["sources"] == []
    assert body["model"] == "mock"
    assert body["fallback"] is True
    assert body["error_type"] == "chunks_not_found"
    assert "chunks artifact was not found" in body["answer"]
    assert body["token_usage"]["input_tokens"] == 6
    assert body["token_usage"]["total_tokens"] == (
        body["token_usage"]["input_tokens"] + body["token_usage"]["output_tokens"]
    )


def test_chat_handles_retrieval_exception_safely() -> None:
    def failing_retriever(*_args) -> list:
        raise RuntimeError("retrieval failed")

    response = handle_chat(
        ChatRequest(message="pod pending"),
        chunk_loader=lambda _path: [],
        retriever=failing_retriever,
    )

    assert response.fallback is True
    assert response.error_type == "retrieval_error"
    assert response.sources == []
    assert response.model == "mock"
    assert response.token_usage.total_tokens == (
        response.token_usage.input_tokens + response.token_usage.output_tokens
    )


def test_chat_handles_prompt_builder_exception_safely() -> None:
    def failing_prompt_builder(*_args) -> str:
        raise RuntimeError("prompt failed")

    response = handle_chat(
        ChatRequest(message="pod pending"),
        chunk_loader=lambda _path: [],
        prompt_builder=failing_prompt_builder,
    )

    assert response.fallback is True
    assert response.error_type == "prompt_build_error"
    assert response.sources == []
    assert response.model == "mock"


def test_chat_handles_provider_exception_safely() -> None:
    response = handle_chat(
        ChatRequest(message="pod pending"),
        chunk_loader=lambda _path: [],
        provider=FailingProvider(),
    )

    assert response.fallback is True
    assert response.error_type == "provider_error"
    assert response.sources == []
    assert response.model == "mock"


def test_chat_handles_provider_timeout_safely() -> None:
    response = handle_chat(
        ChatRequest(message="pod pending"),
        chunk_loader=lambda _path: [],
        provider=SlowProvider(),
        provider_timeout_seconds=0.001,
    )

    assert response.fallback is True
    assert response.error_type == "provider_timeout"
    assert response.sources == []
    assert response.model == "mock"


def test_chat_returns_no_sources_when_retrieval_has_no_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(
        chunks_path,
        [
            {
                "chunk_id": "chunk-cron",
                "document_id": "doc-cron",
                "title": "CronJob Backfill",
                "heading": "CronJob Backfill > Purpose",
                "source_url": None,
                "local_path": "docs/cron.md",
                "content": "Backfill Jobs should avoid duplicate work.",
            }
        ],
    )
    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", chunks_path)

    response = client.post("/chat", json={"message": "unmatched words only"})

    assert response.status_code == 200
    body = response.json()
    assert NO_CONTEXT_RESPONSE in body["answer"]
    assert MOCK_PROVIDER_NOTE in body["answer"]
    assert body["sources"] == []
    assert body["fallback"] is False
    assert body["error_type"] is None


def test_chat_supports_vector_retrieval_mode(tmp_path: Path, monkeypatch) -> None:
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
    persist_directory = tmp_path / "chroma"
    build_vector_index(
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
        persist_directory=persist_directory,
        embedding_provider="hash",
    )
    monkeypatch.setattr("app.services.chat.CHUNKS_PATH", chunks_path)
    monkeypatch.setattr("app.services.chat.CHROMA_PERSIST_DIRECTORY", persist_directory)

    response = client.post(
        "/chat",
        json={
            "message": "Why is my pod pending scheduling?",
            "retrieval_mode": "vector",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["chunk_id"] == "chunk-pending"
    assert body["sources"][0]["score"] > 0


def test_chat_rejects_invalid_retrieval_mode() -> None:
    response = client.post(
        "/chat",
        json={"message": "How does HPA work?", "retrieval_mode": "invalid"},
    )

    assert response.status_code == 422


def test_chat_rejects_empty_message() -> None:
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_rejects_missing_message() -> None:
    response = client.post("/chat", json={})

    assert response.status_code == 422


def write_chunks(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as chunks_file:
        for row in rows:
            chunks_file.write(json.dumps(row) + "\n")


class FailingProvider:
    def generate(self, prompt: str) -> ProviderResponse:
        raise RuntimeError("provider failed")


class SlowProvider:
    def generate(self, prompt: str) -> ProviderResponse:
        sleep(0.05)
        return ProviderResponse(
            text="slow response",
            model="mock",
            input_tokens=len(prompt.split()),
            output_tokens=2,
            total_tokens=len(prompt.split()) + 2,
        )
