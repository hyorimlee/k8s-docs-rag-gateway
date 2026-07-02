from __future__ import annotations

from app.prompting.builder import NO_CONTEXT_MESSAGE, build_prompt
from app.retrieval.simple import RetrievalResult


def test_prompt_includes_user_question() -> None:
    prompt = build_prompt("Why is my Pod Pending?", [retrieval_result()])

    assert "USER QUESTION\nWhy is my Pod Pending?" in prompt


def test_prompt_includes_assistant_boundary_rules() -> None:
    prompt = build_prompt("How should I troubleshoot?", [retrieval_result()])

    assert "Use only the provided context." in prompt
    assert "Do not claim to inspect a live Kubernetes cluster." in prompt
    assert (
        "Do not invent pod names, node names, events, IPs, namespaces, or secrets."
        in prompt
    )
    assert "Do not recommend deleting workloads as a first step." in prompt
    assert "Do not expose or ask for secrets." in prompt


def test_prompt_includes_chunk_metadata_and_content() -> None:
    result = retrieval_result()

    prompt = build_prompt("What should I check?", [result])

    assert "chunk_id: chunk-1" in prompt
    assert "document_id: doc-1" in prompt
    assert "title: Pod Pending Troubleshooting" in prompt
    assert "heading: Pod Pending Troubleshooting > Safe Triage Flow" in prompt
    assert "source_url: https://example.com/pods" in prompt
    assert "local_path: docs/pending.md" in prompt
    assert "score: 12.5" in prompt
    assert "docs_version: local" in prompt
    assert "imported_commit: abc123" in prompt
    assert "Check resource requests and scheduling constraints." in prompt


def test_prompt_includes_source_numbering() -> None:
    prompt = build_prompt(
        "How do I plan a backfill?",
        [
            retrieval_result(chunk_id="chunk-a"),
            retrieval_result(chunk_id="chunk-b"),
        ],
    )

    assert "[1]\nchunk_id: chunk-a" in prompt
    assert "[2]\nchunk_id: chunk-b" in prompt
    assert "Cite sources by source number" in prompt


def test_empty_retrieved_chunks_produces_no_context_prompt() -> None:
    prompt = build_prompt("What does Kubernetes say?", [])

    assert NO_CONTEXT_MESSAGE in prompt
    assert "Do not fabricate an answer from general knowledge." in prompt
    assert "USER QUESTION\nWhat does Kubernetes say?" in prompt


def test_prompt_output_is_deterministic() -> None:
    chunks = [
        retrieval_result(chunk_id="chunk-a"),
        retrieval_result(chunk_id="chunk-b"),
    ]

    assert build_prompt("Question?", chunks) == build_prompt("Question?", chunks)


def test_prompt_truncates_context_content_deterministically() -> None:
    prompt = build_prompt(
        "Question?",
        [retrieval_result(content="0123456789" * 10)],
        max_context_chars=30,
    )

    assert "012345678901234\n[truncated]" in prompt


def retrieval_result(
    *,
    chunk_id: str = "chunk-1",
    content: str = "Check resource requests and scheduling constraints.",
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        title="Pod Pending Troubleshooting",
        heading="Pod Pending Troubleshooting > Safe Triage Flow",
        source_url="https://example.com/pods",
        local_path="docs/pending.md",
        score=12.5,
        content=content,
        docs_version="local",
        imported_commit="abc123",
        collection_ids=["pod-pending-troubleshooting"],
        tags=["pod-pending", "scheduling"],
        category="custom-runbook",
        priority="p0",
        language="en",
    )
