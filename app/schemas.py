"""Request and response schemas for the API."""

from datetime import datetime
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
    retrieval_mode: str = Field(default="keyword")


class TokenUsage(BaseModel):
    """Token usage metadata for a chat response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class Source(BaseModel):
    """Source metadata returned for retrieved documentation chunks."""

    chunk_id: str
    document_id: str
    title: str
    heading: Optional[str] = None
    source_url: Optional[str] = None
    local_path: str
    score: float
    docs_version: Optional[str] = None
    imported_commit: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response returned by the chat endpoint."""

    request_id: str
    answer: str
    sources: list[Source]
    model: str
    latency_ms: float
    token_usage: TokenUsage
    fallback: bool
    error_type: Optional[str] = None


class RetrievedChunkTrace(BaseModel):
    """Retrieved chunk metadata and content stored in an in-memory trace."""

    chunk_id: str
    document_id: str
    title: str
    heading: Optional[str] = None
    source_url: Optional[str] = None
    local_path: str
    score: float
    content: str
    docs_version: Optional[str] = None
    imported_commit: Optional[str] = None
    retrieval_mode: str = "keyword"


class TraceResponse(BaseModel):
    """Stored chat execution trace."""

    request_id: str
    question: str
    answer: str
    sources: list[Source]
    retrieved_chunks: list[RetrievedChunkTrace]
    prompt: str
    model: str
    token_usage: TokenUsage
    latency_ms: float
    fallback: bool
    error_type: Optional[str] = None
    retrieval_mode: str = "keyword"
    retriever_name: str = "keyword_retriever"
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    created_at: datetime
