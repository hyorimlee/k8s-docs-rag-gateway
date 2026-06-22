from __future__ import annotations

from app.providers.base import LLMProvider, ProviderResponse
from app.providers.mock import MOCK_PROVIDER_TEXT, MockLLMProvider


def test_mock_provider_returns_deterministic_text() -> None:
    provider = MockLLMProvider()

    first = provider.generate("Use this prompt.")
    second = provider.generate("Use this prompt.")

    assert first.text == MOCK_PROVIDER_TEXT
    assert second.text == MOCK_PROVIDER_TEXT
    assert first == second


def test_mock_provider_returns_mock_model() -> None:
    response = MockLLMProvider().generate("prompt")

    assert response.model == "mock"


def test_mock_provider_token_usage_is_consistent() -> None:
    response = MockLLMProvider().generate("one two three")

    assert response.input_tokens == 3
    assert response.output_tokens == len(MOCK_PROVIDER_TEXT.split())
    assert response.total_tokens == response.input_tokens + response.output_tokens


def test_mock_provider_handles_empty_prompt_deterministically() -> None:
    response = MockLLMProvider().generate("")

    assert response.input_tokens == 0
    assert response.text == MOCK_PROVIDER_TEXT
    assert response.total_tokens == response.output_tokens


def test_mock_provider_satisfies_provider_protocol() -> None:
    provider: LLMProvider = MockLLMProvider()

    response = provider.generate("prompt")

    assert isinstance(response, ProviderResponse)
