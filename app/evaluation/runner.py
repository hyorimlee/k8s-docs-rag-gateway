from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.retrieval.loader import DEFAULT_CHUNKS_PATH
from app.schemas import ChatRequest, ChatResponse, TraceResponse
from app.services.chat import handle_chat
from app.tracing.store import get_trace

DEFAULT_CASES_PATH = Path("eval/cases.yaml")


@dataclass(frozen=True)
class EvalExpectations:
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    answer_must_contain: list[str] = field(default_factory=list)
    answer_must_not_contain: list[str] = field(default_factory=list)
    prompt_must_contain: list[str] = field(default_factory=list)
    prompt_must_not_contain: list[str] = field(default_factory=list)
    source_must_contain: list[str] = field(default_factory=list)
    min_source_count: int = 0
    min_retrieved_chunk_count: int = 0
    require_sources: bool = False
    require_trace: bool = True
    require_prompt: bool = False
    require_retrieved_chunks: bool = False
    require_token_usage: bool = True
    allow_fallback: bool = False
    expect_fallback: bool | None = None
    expect_error_type: str | None = None


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    message: str
    top_k: int
    expectations: EvalExpectations


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    passed: bool
    failures: list[str]
    response: ChatResponse
    trace: TraceResponse | None


def load_eval_cases(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [_parse_case(case) for case in raw.get("cases", [])]


def run_eval_cases(
    cases: list[EvalCase],
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
) -> list[EvalResult]:
    return [run_eval_case(case, chunks_path=chunks_path) for case in cases]


def run_eval_case(
    case: EvalCase,
    *,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
) -> EvalResult:
    response = handle_chat(
        ChatRequest(message=case.message, top_k=case.top_k),
        chunks_path=chunks_path,
    )
    trace = get_trace(response.request_id)
    failures = check_expectations(case.expectations, response, trace)

    return EvalResult(
        case_id=case.case_id,
        passed=not failures,
        failures=failures,
        response=response,
        trace=trace,
    )


def check_expectations(
    expectations: EvalExpectations,
    response: ChatResponse,
    trace: TraceResponse | None,
) -> list[str]:
    failures: list[str] = []
    searchable_text = _searchable_text(response, trace)
    answer_text = response.answer.lower()
    prompt_text = trace.prompt.lower() if trace is not None else ""
    source_text = "\n".join(
        source.model_dump_json() for source in response.sources
    ).lower()

    for expected_text in expectations.must_contain:
        if expected_text.lower() not in searchable_text:
            failures.append(f"missing expected text: {expected_text}")

    for forbidden_text in expectations.must_not_contain:
        if forbidden_text.lower() in searchable_text:
            failures.append(f"found forbidden text: {forbidden_text}")

    for expected_text in expectations.answer_must_contain:
        if expected_text.lower() not in answer_text:
            failures.append(f"expected answer to contain: {expected_text}")

    for forbidden_text in expectations.answer_must_not_contain:
        if forbidden_text.lower() in answer_text:
            failures.append(f"expected answer not to contain: {forbidden_text}")

    for expected_text in expectations.prompt_must_contain:
        if expected_text.lower() not in prompt_text:
            failures.append(f"expected prompt to contain: {expected_text}")

    for forbidden_text in expectations.prompt_must_not_contain:
        if forbidden_text.lower() in prompt_text:
            failures.append(f"expected prompt not to contain: {forbidden_text}")

    for expected_text in expectations.source_must_contain:
        if expected_text.lower() not in source_text:
            failures.append(f"expected source metadata to contain: {expected_text}")

    if expectations.require_sources and not response.sources:
        failures.append("expected at least one source")

    if len(response.sources) < expectations.min_source_count:
        failures.append(
            "expected at least "
            f"{expectations.min_source_count} sources, got {len(response.sources)}"
        )

    if response.fallback and not expectations.allow_fallback:
        failures.append(f"unexpected fallback: {response.error_type}")

    if (
        expectations.expect_fallback is not None
        and response.fallback is not expectations.expect_fallback
    ):
        failures.append(
            f"expected fallback={expectations.expect_fallback} "
            f"but got {response.fallback}"
        )

    if response.error_type != expectations.expect_error_type:
        failures.append(
            "unexpected error_type: "
            f"expected {expectations.expect_error_type}, got {response.error_type}"
        )

    if expectations.require_trace and trace is None:
        failures.append("trace was not saved")
        return failures

    if trace is not None:
        if expectations.require_prompt and not trace.prompt:
            failures.append("expected trace prompt to be present")

        if len(trace.retrieved_chunks) < expectations.min_retrieved_chunk_count:
            failures.append(
                "expected at least "
                f"{expectations.min_retrieved_chunk_count} retrieved chunks, "
                f"got {len(trace.retrieved_chunks)}"
            )

        if expectations.require_retrieved_chunks and not trace.retrieved_chunks:
            failures.append("expected trace retrieved chunks to be present")

        if trace.fallback != response.fallback:
            failures.append("trace fallback did not match response fallback")

        if trace.error_type != response.error_type:
            failures.append("trace error_type did not match response error_type")

    if expectations.require_token_usage and not _valid_token_usage(response):
        failures.append("token usage was missing or invalid")

    return failures


def _parse_case(raw: dict[str, Any]) -> EvalCase:
    expectations = raw.get("expectations") or {}
    return EvalCase(
        case_id=str(raw["id"]),
        message=str(raw["message"]),
        top_k=int(raw.get("top_k", 5)),
        expectations=EvalExpectations(
            must_contain=list(expectations.get("must_contain") or []),
            must_not_contain=list(expectations.get("must_not_contain") or []),
            answer_must_contain=list(expectations.get("answer_must_contain") or []),
            answer_must_not_contain=list(
                expectations.get("answer_must_not_contain") or []
            ),
            prompt_must_contain=list(expectations.get("prompt_must_contain") or []),
            prompt_must_not_contain=list(
                expectations.get("prompt_must_not_contain") or []
            ),
            source_must_contain=list(expectations.get("source_must_contain") or []),
            min_source_count=int(expectations.get("min_source_count", 0)),
            min_retrieved_chunk_count=int(
                expectations.get("min_retrieved_chunk_count", 0)
            ),
            require_sources=bool(expectations.get("require_sources", False)),
            require_trace=bool(expectations.get("require_trace", True)),
            require_prompt=bool(expectations.get("require_prompt", False)),
            require_retrieved_chunks=bool(
                expectations.get("require_retrieved_chunks", False)
            ),
            require_token_usage=bool(expectations.get("require_token_usage", True)),
            allow_fallback=bool(expectations.get("allow_fallback", False)),
            expect_fallback=expectations.get("expect_fallback"),
            expect_error_type=expectations.get("expect_error_type"),
        ),
    )


def _searchable_text(response: ChatResponse, trace: TraceResponse | None) -> str:
    parts = [response.answer]
    parts.extend(source.model_dump_json() for source in response.sources)

    if trace is not None:
        parts.extend(
            [
                trace.question,
                trace.answer,
                trace.prompt,
                trace.model_dump_json(),
            ]
        )

    return "\n".join(parts).lower()


def _valid_token_usage(response: ChatResponse) -> bool:
    usage = response.token_usage
    if usage.input_tokens < 0 or usage.output_tokens < 0 or usage.total_tokens < 0:
        return False
    return usage.total_tokens == usage.input_tokens + usage.output_tokens
