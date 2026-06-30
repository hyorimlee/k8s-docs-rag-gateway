from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.runner import (
    EvalExpectations,
    check_expectations,
    load_eval_cases,
    run_eval_case,
)
from app.schemas import ChatResponse, TokenUsage
from app.tracing.store import clear_traces


@pytest.fixture(autouse=True)
def clear_trace_store() -> None:
    clear_traces()


def test_eval_cases_file_loads() -> None:
    cases = load_eval_cases()

    case_ids = {case.case_id for case in cases}

    assert "pod_pending_triage" in case_ids
    assert "cronjob_backfill_safety" in case_ids
    assert "live_cluster_boundary" in case_ids
    assert "secret_handling" in case_ids
    assert "unknown_context" in case_ids


def test_eval_runner_executes_passing_case_against_fixture_chunks(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    write_chunks(
        chunks_path,
        [
            {
                "chunk_id": "chunk-pending",
                "document_id": "doc-pending",
                "title": "Pod Pending Troubleshooting Checklist",
                "heading": "Pod Pending Troubleshooting Checklist > Safe Triage Flow",
                "source_url": None,
                "local_path": "docs/pending.md",
                "docs_version": "local",
                "imported_commit": None,
                "collection_ids": ["pod-pending-troubleshooting"],
                "tags": ["pod-pending", "scheduling"],
                "category": "custom-runbook",
                "priority": "p0",
                "language": "en",
                "content": "Check resource requests and scheduling constraints.",
            }
        ],
    )
    case = next(
        case for case in load_eval_cases() if case.case_id == "pod_pending_triage"
    )

    result = run_eval_case(case, chunks_path=chunks_path)

    assert result.passed is True
    assert result.failures == []
    assert result.response.sources
    assert result.trace is not None


def test_failing_expectation_produces_failed_result() -> None:
    response = ChatResponse(
        request_id="request-1",
        answer="mock answer",
        sources=[],
        model="mock",
        latency_ms=1.0,
        token_usage=TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        fallback=False,
        error_type=None,
    )

    failures = check_expectations(
        EvalExpectations(must_contain=["definitely absent"], require_sources=True),
        response,
        trace=None,
    )

    assert "missing expected text: definitely absent" in failures
    assert "expected at least one source" in failures
    assert "trace was not saved" in failures


def test_eval_runner_reports_missing_chunks_clearly(tmp_path: Path) -> None:
    case = next(
        case for case in load_eval_cases() if case.case_id == "pod_pending_triage"
    )

    result = run_eval_case(case, chunks_path=tmp_path / "missing.jsonl")

    assert result.passed is False
    assert result.response.fallback is True
    assert result.response.error_type == "chunks_not_found"
    assert "unexpected fallback: chunks_not_found" in result.failures


def write_chunks(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as chunks_file:
        for row in rows:
            chunks_file.write(json.dumps(row) + "\n")
