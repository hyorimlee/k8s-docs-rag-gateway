from __future__ import annotations

from app.providers.base import ProviderResponse, estimate_tokens

MOCK_PROVIDER_TEXT = (
    "This is a mock provider response generated from the provided prompt. "
    "Real LLM generation is not implemented yet."
)


class MockLLMProvider:
    model = "mock"

    def generate(self, prompt: str) -> ProviderResponse:
        input_tokens = estimate_tokens(prompt)
        output_tokens = estimate_tokens(MOCK_PROVIDER_TEXT)

        return ProviderResponse(
            text=MOCK_PROVIDER_TEXT,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
