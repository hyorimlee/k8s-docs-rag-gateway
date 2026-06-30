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
    require_sources: bool = False
    allow_fallback: bool = False
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

    for expected_text in expectations.must_contain:
        if expected_text.lower() not in searchable_text:
            failures.append(f"missing expected text: {expected_text}")

    for forbidden_text in expectations.must_not_contain:
        if forbidden_text.lower() in searchable_text:
            failures.append(f"found forbidden text: {forbidden_text}")

    if expectations.require_sources and not response.sources:
        failures.append("expected at least one source")

    if response.fallback and not expectations.allow_fallback:
        failures.append(f"unexpected fallback: {response.error_type}")

    if response.error_type != expectations.expect_error_type:
        failures.append(
            "unexpected error_type: "
            f"expected {expectations.expect_error_type}, got {response.error_type}"
        )

    if trace is None:
        failures.append("trace was not saved")

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
            require_sources=bool(expectations.get("require_sources", False)),
            allow_fallback=bool(expectations.get("allow_fallback", False)),
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
