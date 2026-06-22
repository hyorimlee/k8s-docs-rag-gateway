"""FastAPI application entrypoint."""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI

from app.config import APP_ENV, APP_NAME, APP_VERSION
from app.schemas import ChatRequest, ChatResponse, HealthResponse, TokenUsage

app = FastAPI(title=APP_NAME, version=APP_VERSION)

MOCK_CHAT_ANSWER = (
    "This is a mock response. Retrieval and LLM generation are not implemented yet."
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return basic service health information."""
    return HealthResponse(
        status="ok",
        service=APP_NAME,
        environment=APP_ENV,
        version=APP_VERSION,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Return a deterministic mock chat response."""
    started_at = perf_counter()
    input_tokens = len(request.message.split())
    output_tokens = len(MOCK_CHAT_ANSWER.split())
    latency_ms = (perf_counter() - started_at) * 1000

    return ChatResponse(
        request_id=str(uuid4()),
        answer=MOCK_CHAT_ANSWER,
        sources=[],
        model="mock",
        latency_ms=latency_ms,
        token_usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
        fallback=False,
        error_type=None,
    )
