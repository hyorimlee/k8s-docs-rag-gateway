"""Request and response schemas for the API."""

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    environment: str
    version: str


class ChatRequest(BaseModel):
    """Chat request for the mock API contract."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    message: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    mode: str = "mock"


class TokenUsage(BaseModel):
    """Token usage metadata for a chat response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    """Chat response returned by the mock endpoint."""

    request_id: str
    answer: str
    sources: list[dict[str, str]]
    model: str
    latency_ms: float
    token_usage: TokenUsage
    fallback: bool
    error_type: Optional[str] = None
