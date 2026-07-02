from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> ProviderResponse:
        """Generate a response for a prompt."""


def estimate_tokens(text: str) -> int:
    return len(text.split())
