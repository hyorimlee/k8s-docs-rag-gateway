"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException

from app.config import APP_ENV, APP_NAME, APP_VERSION
from app.schemas import ChatRequest, ChatResponse, HealthResponse, TraceResponse
from app.services.chat import handle_chat
from app.tracing.store import get_trace

app = FastAPI(title=APP_NAME, version=APP_VERSION)


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
    """Run the local mock RAG-style chat flow."""
    if request.retrieval_mode not in {"keyword", "vector"}:
        raise HTTPException(status_code=422, detail="Invalid retrieval_mode")
    return handle_chat(request)


@app.get("/traces/{request_id}", response_model=TraceResponse)
def trace(request_id: str) -> TraceResponse:
    """Return an in-memory chat execution trace."""
    stored_trace = get_trace(request_id)
    if stored_trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return stored_trace
