from __future__ import annotations

from app.providers.base import LLMProvider, ProviderResponse
from app.providers.mock import (
    CONTEXT_RESPONSE_INTRO,
    MOCK_PROVIDER_NOTE,
    NO_CONTEXT_RESPONSE,
    MockLLMProvider,
)


def test_mock_provider_returns_deterministic_text() -> None:
    provider = MockLLMProvider()
    prompt = context_prompt()

    first = provider.generate(prompt)
    second = provider.generate(prompt)

    assert first.text == second.text
    assert first == second


def test_mock_provider_context_response_is_not_old_generic_sentence() -> None:
    response = MockLLMProvider().generate(context_prompt())

    assert response.text != (
        "This is a mock provider response generated from the provided prompt. "
        "Real LLM generation is not implemented yet."
    )


def test_mock_provider_context_response_mentions_context_and_checklist() -> None:
    response = MockLLMProvider().generate(context_prompt())

    assert CONTEXT_RESPONSE_INTRO in response.text
    assert "1. Review the documented diagnostic signals" in response.text
    assert (
        "2. Check scheduling, workload, or configuration constraints" in response.text
    )
    assert "3. Prefer safe diagnostic checks" in response.text
    assert MOCK_PROVIDER_NOTE in response.text


def test_mock_provider_context_response_includes_parsed_source_label() -> None:
    response = MockLLMProvider().generate(context_prompt())

    assert "Sources used:" in response.text
    assert (
        "- Pod Pending Troubleshooting - Pod Pending Troubleshooting > Safe Triage Flow"
    ) in response.text


def test_mock_provider_no_context_response_is_safe() -> None:
    response = MockLLMProvider().generate(
        "CONTEXT\nNo relevant documentation context was provided.\n"
        "Do not fabricate an answer from general knowledge."
    )

    assert NO_CONTEXT_RESPONSE in response.text
    assert "should not fabricate" in response.text
    assert "Sources used:" not in response.text
    assert MOCK_PROVIDER_NOTE in response.text


def test_mock_provider_returns_mock_model() -> None:
    response = MockLLMProvider().generate("prompt")

    assert response.model == "mock"


def test_mock_provider_token_usage_is_consistent() -> None:
    response = MockLLMProvider().generate(context_prompt())

    assert response.input_tokens > 0
    assert response.output_tokens == len(response.text.split())
    assert response.total_tokens == response.input_tokens + response.output_tokens


def test_mock_provider_handles_empty_prompt_deterministically() -> None:
    response = MockLLMProvider().generate("")

    assert response.input_tokens == 0
    assert response.output_tokens >= 0
    assert response.total_tokens == response.output_tokens


def test_mock_provider_satisfies_provider_protocol() -> None:
    provider: LLMProvider = MockLLMProvider()

    response = provider.generate("prompt")

    assert isinstance(response, ProviderResponse)


def context_prompt() -> str:
    return "\n".join(
        [
            "CONTEXT",
            "[1]",
            "chunk_id: chunk-1",
            "document_id: doc-1",
            "title: Pod Pending Troubleshooting",
            "heading: Pod Pending Troubleshooting > Safe Triage Flow",
            "content:",
            "Check resource requests and scheduling constraints.",
            "",
            "USER QUESTION",
            "Why is my Pod Pending?",
        ]
    )
